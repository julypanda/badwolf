# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import logging

import git
from unidiff import PatchSet, UnidiffParseError

from badwolf.extensions import bitbucket
from badwolf.bitbucket import PullRequest, BitbucketAPIError
from badwolf.lint import Problems
from badwolf.lint.linters.eslint import ESLinter
from badwolf.lint.linters.flake8 import Flake8Linter
from badwolf.lint.linters.jscs import JSCSLinter


logger = logging.getLogger(__name__)


class LintProcessor(object):
    LINTERS = {
        'eslint': ESLinter,
        'flake8': Flake8Linter,
        'jscs': JSCSLinter,
    }

    def __init__(self, context, spec, working_dir):
        self.context = context
        self.spec = spec
        self.working_dir = working_dir
        self.problems = Problems()
        self.pr = PullRequest(bitbucket, context.repository)

    def load_changes(self):
        git_cmd = git.Git(self.working_dir)
        revision_before = self.context.target['commit']['hash']
        revision_after = self.context.source['commit']['hash']
        changes = None
        try:
            #  优先从本地 git 仓库获取 diff
            diff = git_cmd.diff(revision_before, revision_after, color='never')
            if diff:
                changes = PatchSet(diff.split('\n'))
        except (git.GitCommandError, UnidiffParseError):
            logger.exception('Error getting git diff from local repository')

        if not changes:
            # 失败则调用 Bitbucket API 获取 diff
            try:
                changes = self.pr.diff(self.context.pr_id)
            except (BitbucketAPIError, UnidiffParseError):
                logger.exception('Error getting pull request diff from API')
                return

        self.problems.set_changes(changes)
        return changes

    def process(self):
        if not self.spec.linters:
            logger.info('No linters configured, ignore lint.')
            return

        logger.info('Running code linting')
        patch = self.load_changes()
        if not patch:
            logger.info('Load changes failed, ignore lint.')
            return

        lint_files = patch.added_files + patch.modified_files
        if not lint_files:
            logger.info('No changed files found, ignore lint')
            return

        files = [f.path for f in lint_files]
        try:
            # python-unidiff 0.5.2+
            self.lint_file_revisions = {f.path: (f.revision_before, f.revision_after) for f in lint_files}
        except AttributeError:
            revision_before = self.context.target['commit']['hash']
            revision_after = self.context.source['commit']['hash']
            self.lint_file_revisions = {f.path: (revision_before, revision_after) for f in lint_files}

        self._execute_linters(files)
        self.problems.limit_to_changes()

        if len(self.problems):
            self._report()
        else:
            logger.info('No problems found when linting codes')

    def _execute_linters(self, files):
        for name in self.spec.linters:
            linter_cls = self.LINTERS.get(name)
            if not linter_cls:
                logger.info('Linter %s not found, ignore.', name)
                continue

            linter = linter_cls(self.working_dir, self.problems)
            if not linter.is_usable():
                logger.info('Linter %s is not usable, ignore.', name)
                continue

            logger.info('Running %s code linter', name)
            linter.execute(files)

    def _report(self):
        try:
            comments = self.pr.all_comments(self.context.pr_id)
        except BitbucketAPIError:
            logger.exception('Error fetching all comments for pull request')
            comments = []

        hash_set = set()
        for comment in comments:
            inline = comment.get('inline')
            if not inline:
                continue

            raw = comment['content']['raw']
            filename = inline['path']
            line_to = inline['to']
            hash_set.add(hash('{}{}{}'.format(filename, line_to, raw)))

        problem_count = 0
        for problem in self.problems:
            content = ':broken_heart: **{}**: {}'.format(problem.linter, problem.message)
            comment_hash = hash('{}{}{}'.format(
                problem.filename,
                problem.line,
                content,
            ))
            if comment_hash in hash_set:
                continue

            revision = self.lint_file_revisions.get(problem.filename, (None, None))
            try:
                self.pr.comment(
                    self.context.pr_id,
                    content,
                    line_to=problem.line,
                    filename=problem.filename,
                    anchor=revision[1],
                    dest_rev=revision[0],
                )
            except BitbucketAPIError:
                logger.exception('Error creating inline comment for pull request')
            else:
                problem_count += 1

        logger.info('Code lint result: %d problems submited', problem_count)
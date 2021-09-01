import os
import sys
import shutil

import dotbot

class CrossPlatformLink(dotbot.plugins.Link, dotbot.Plugin):
    '''
    Symbolically links dotfiles.
    '''

    _directive = 'crossplatform-link'

    def parse_environment(self, environment_val) -> bool:
            if environment_val is None:
                return True
            
            if len(environment_val) > 0 and environment_val[0] == "!":
                reverse_it = True
                environment_val = environment_val[1:]
            else:
                reverse_it = False

            if len(environment_val) == 0:
                raise ValueError(f"Malformed environment argument: {environment_val}")

            if "=" in environment_val:
                environment_val, val = environment_val.split("=", 1)

                result = os.environ.get(environment_val) == val
            else:
                result = os.environ.get(environment_val) is not None

            if reverse_it:
                return not result
            else:
                return result

    def parse_platform(self, platform_val) -> bool:
        return platform_val is None or platform_val.lower() == sys.platform.lower()

    def _default_source(self, destination, source):
        if source is None:
            basename = os.path.basename(destination)
            if basename.startswith('.'):
                return basename[1:]
            else:
                return basename
        else:
            return os.path.normpath(source)

    def handle(self, directive, data) -> bool:
        if directive != self._directive:
            raise ValueError('CrossPlatform-Link cannot handle directive %s' % directive)
        did_error = False
        
        processed_data = {}

        defaults = self._context.defaults().get('link-crossplatform', {})
        fallback_to_copy_default = defaults.get("fallback_to_copy", False)

        self._fallback_to_copy = {}

        default_platform = self.parse_platform(defaults.get('platform'))
        try:
            default_environment = self.parse_environment(defaults.get('environment'))
        except Exception as ex:
            self._log.error(f"Cannot parse default environment value, ignoring it: {defaults.get('environment')}")
            did_error = True
        
        for destination, source in data.items():
            # Fix destination, source
            destination = os.path.normpath(destination)
            self._fallback_to_copy[destination] = fallback_to_copy_default
            if isinstance(source, dict):
                platform = self.parse_platform(source.get('platform')) and default_platform
                self._fallback_to_copy[destination] = source.get("fallback_to_copy", fallback_to_copy_default)
                try:
                    environment = self.parse_environment(source.get('environment')) and default_environment
                except Exception as ex:
                    self._log.error(f"Cannot parse default environment argument '{source.get('environment')}' for destination '{destination}', ignoring it")
                    did_error = True
                if platform and environment:
                    processed_data[destination] = source
                else:
                    self._log.lowinfo("Skipping %s" % destination)
            else:
                processed_data[destination] = source

        return self._process_links(processed_data) and not did_error

    def _link(self, source, link_name, relative, canonical_path, ignore_missing):
        '''
        Links link_name to source.
        Returns true if successfully linked files.
        '''
        success = False
        link_source = link_name
        fallback_to_copy = self._fallback_to_copy.get(link_name)
        while fallback_to_copy is not None and link_source != os.path.dirname(link_source):
            link_source = os.path.dirname(link_source)
            fallback_to_copy = self._fallback_to_copy.get(link_source)

        destination = os.path.expanduser(link_name)
        base_directory = self._context.base_directory(canonical_path=canonical_path)
        absolute_source = os.path.join(base_directory, source)
        if relative:
            source = self._relative_path(absolute_source, destination)
        else:
            source = absolute_source
        if (not self._exists(link_name) and self._is_link(link_name) and
                self._link_destination(link_name) != source):
            self._log.warning('Invalid link %s -> %s' %
                (link_name, self._link_destination(link_name)))
        # we need to use absolute_source below because our cwd is the dotfiles
        # directory, and if source is relative, it will be relative to the
        # destination directory
        elif not self._exists(link_name) and (ignore_missing or self._exists(absolute_source)):
            try:
                os.symlink(source, destination)
            except OSError:
                self._log.warning('Linking failed %s -> %s' % (link_name, source))
                if fallback_to_copy:
                    self._log.lowinfo('Falling back to directly copying file')
                    shutil.copyfile(source, destination)
                    success = True
            else:
                self._log.lowinfo('Creating link %s -> %s' % (link_name, source))
                success = True
        elif self._exists(link_name) and not self._is_link(link_name):
            self._log.warning(
                '%s already exists but is a regular file or directory' %
                link_name)
        elif self._is_link(link_name) and self._link_destination(link_name) != source:
            self._log.warning('Incorrect link %s -> %s' %
                (link_name, self._link_destination(link_name)))
        # again, we use absolute_source to check for existence
        elif not self._exists(absolute_source):
            if self._is_link(link_name):
                self._log.warning('Nonexistent source %s -> %s' %
                    (link_name, source))
            else:
                self._log.warning('Nonexistent source for %s : %s' %
                    (link_name, source))
        else:
            self._log.lowinfo('Link exists %s -> %s' % (link_name, source))
            success = True
        return success
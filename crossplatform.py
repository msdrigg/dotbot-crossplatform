import os
import sys

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

        default_platform = self.parse_platform(defaults.get('platform'))
        try:
            default_environment = self.parse_environment(defaults.get('environment'))
        except Exception as ex:
            self._log.error(f"Cannot parse default environment value, ignoring it: {defaults.get('environment')}")
            did_error = True
        
        for destination, source in data.items():
            # Fix destination, source
            destination = os.path.normpath(destination)
            if isinstance(source, dict):
                platform = self.parse_platform(source.get('platform')) and default_platform
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

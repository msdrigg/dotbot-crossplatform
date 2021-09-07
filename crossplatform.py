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
        if platform_val is None:
            return True

        if len(platform_val) > 0 and platform_val[0] == "!":
            reverse_it = True
            platform_val = platform_val[1:]
        else:
            reverse_it = False
        result = platform_val.lower() == sys.platform.lower()

        if reverse_it:
            return not result
        else:
            return result
    
    def _normalize_path(self, path):
        new_path = os.path.normpath(path)
        if path[-1] == "/" or path.endswith(os.sep):
            return f"{new_path}{os.sep}"
        return new_path
    
    def _default_source(self, destination, source):
        if source is None:
            basename = os.path.basename(destination)
            if basename.startswith('.'):
                return basename[1:]
            else:
                return basename
        else:
            return self._normalize_path(source)

    def handle(self, directive, data) -> bool:
        if directive != self._directive:
            raise ValueError('CrossPlatform-Link cannot handle directive %s' % directive)
        did_error = False
        
        processed_data = []

        defaults = self._context.defaults().get(self._directive, {})

        default_platform = self.parse_platform(defaults.get('platform'))
        try:
            default_environment = self.parse_environment(defaults.get('environment'))
        except Exception as ex:
            self._log.error(f"Cannot parse default environment value, ignoring it: {defaults.get('environment')}")
            did_error = True
        
        if isinstance(data, dict):
            items = data.items()
        elif isinstance(data, list):
            items = []
            for item in data:
                for k, v in item.items():
                    items.append((k, v))
        else:
            raise ValueError("CrossPlatform-Link only handles data of type dictionary or list of dictionaries")
        for destination, source in items:
            # Fix destination, source
            destination = self._normalize_path(destination)
            if isinstance(source, dict):
                platform = self.parse_platform(source.get('platform')) and default_platform
                try:
                    environment = self.parse_environment(source.get('environment')) and default_environment
                except Exception as ex:
                    self._log.error(f"Cannot parse default environment argument '{source.get('environment')}' for destination '{destination}', ignoring it")
                    did_error = True
                if platform and environment:
                    processed_data.append((destination, source))
                else:
                    self._log.lowinfo("Skipping %s -> %s" % (destination, self._default_source(destination, source.get('path'))))
            else:
                processed_data.append((destination, source))


        return self._process_links(processed_data) and not did_error

    def _process_links(self, link_tuples):
        success = True
        defaults = self._context.defaults().get(self._directive, {})
        for destination, source in link_tuples:
            destination = os.path.expandvars(destination)
            relative = defaults.get('relative', False)
            # support old "canonicalize-path" key for compatibility
            canonical_path = defaults.get('canonicalize', defaults.get('canonicalize-path', True))
            force = defaults.get('force', False)
            relink = defaults.get('relink', False)
            create = defaults.get('create', False)
            use_glob = defaults.get('glob', False)
            base_prefix = defaults.get('prefix', '')
            test = defaults.get('if', None)
            ignore_missing = defaults.get('ignore-missing', False)
            exclude_paths = defaults.get('exclude', [])
            fallback_to_copy = defaults.get('fallback_to_copy', False)
            if isinstance(source, dict):
                # extended config
                test = source.get('if', test)
                relative = source.get('relative', relative)
                canonical_path = source.get('canonicalize', source.get('canonicalize-path', canonical_path))
                force = source.get('force', force)
                relink = source.get('relink', relink)
                create = source.get('create', create)
                use_glob = source.get('glob', use_glob)
                base_prefix = source.get('prefix', base_prefix)
                ignore_missing = source.get('ignore-missing', ignore_missing)
                exclude_paths = source.get('exclude', exclude_paths)
                fallback_to_copy = source.get('fallback_to_copy', fallback_to_copy)
                path = self._default_source(destination, source.get('path'))
            else:
                path = self._default_source(destination, source)
            if test is not None and not self._test_success(test):
                self._log.lowinfo('Skipping %s' % destination)
                continue
            path = os.path.expandvars(os.path.expanduser(path))
            if use_glob:
                glob_results = self._create_glob_results(path, exclude_paths)
                if len(glob_results) == 0:
                    self._log.warning("Globbing couldn't find anything matching " + str(path))
                    success = False
                    continue
                if len(glob_results) == 1 and (destination[-1] == '/' or destination.endswith(os.sep)):
                    self._log.error("Ambiguous action requested.")
                    self._log.error("No wildcard in glob, directory use undefined: " +
                        destination + " -> " + str(glob_results))
                    self._log.warning("Did you want to link the directory or into it?")
                    success = False
                    continue
                elif len(glob_results) == 1 and not (destination[-1] == '/' or destination.endswith(os.sep)):
                    # perform a normal link operation
                    if create:
                        success &= self._create(destination)
                    if force or relink:
                        success &= self._delete(path, destination, relative, canonical_path, force)
                    success &= self._link(path, destination, relative, canonical_path, ignore_missing, fallback_to_copy)
                else:
                    self._log.lowinfo("Globs from '" + path + "': " + str(glob_results))
                    for glob_full_item in glob_results:
                        # Find common dirname between pattern and the item:
                        glob_dirname = os.path.dirname(os.path.commonprefix([path, glob_full_item]))
                        glob_item = (glob_full_item if len(glob_dirname) == 0 else glob_full_item[len(glob_dirname) + 1:])
                        # Add prefix to basepath, if provided
                        if base_prefix:
                            glob_item = base_prefix + glob_item
                        # where is it going
                        glob_link_destination = os.path.join(destination, glob_item)
                        if create:
                            success &= self._create(glob_link_destination)
                        if force or relink:
                            success &= self._delete(glob_full_item, glob_link_destination, relative, canonical_path, force)
                        success &= self._link(glob_full_item, glob_link_destination, relative, canonical_path, ignore_missing, fallback_to_copy)
            else:
                if create:
                    success &= self._create(destination)
                if not ignore_missing and not self._exists(os.path.join(self._context.base_directory(), path)):
                    # we seemingly check this twice (here and in _link) because
                    # if the file doesn't exist and force is True, we don't
                    # want to remove the original (this is tested by
                    # link-force-leaves-when-nonexistent.bash)
                    success = False
                    self._log.warning('Nonexistent source %s -> %s' %
                        (destination, path))
                    continue
                if force or relink:
                    success &= self._delete(path, destination, relative, canonical_path, force)
                success &= self._link(path, destination, relative, canonical_path, ignore_missing, fallback_to_copy)
        if success:
            self._log.info('All links have been set up')
        else:
            self._log.error('Some links were not successfully set up')
        return success

    def _link(self, source, link_name, relative, canonical_path, ignore_missing, fallback_to_copy=False):
        '''
        Links link_name to source.
        Returns true if successfully linked files.
        '''
        success = False

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
                    self._log.lowinfo('Falling back to directly copying file for %s -> %s' % (link_name, source))
                    try:
                        shutil.copyfile(source, destination)
                        success = True
                    except Exception as ex:
                        self._log.warning(f"Copying failed with error {ex}")
                else:
                    self._log.lowinfo(f"Not falling back to copy for {link_name}")
            else:
                self._log.lowinfo('Creating link %s -> %s' % (link_name, source))
                success = True
        elif self._exists(link_name) and not self._is_link(link_name):
            self._log.warning(
                'Linking %s -> %s failed because %s already exists but is a regular file or directory' %
                (link_name, source, link_name))
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
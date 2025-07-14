project('echo', 'c',
  version: '1.0.1',
  meson_version: '>= 0.62.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

# Import Python module
python = import('python')
python3 = python.find_installation('python3')
python_dir = python3.get_install_dir()

# Import GNOME module for GSettings and GResource
gnome = import('gnome')

# Import i18n module
i18n = import('i18n')

# Find blueprint compiler
blueprint_compiler = find_program('blueprint-compiler', required: false)
if not blueprint_compiler.found()
  subproject('blueprint-compiler')
  blueprint_compiler = find_program('blueprint-compiler', required: true)
endif

# Project configuration
project_id = 'io.github.tobagin.echo'
project_name = 'Echo'
pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'echo')
localedir = join_paths(get_option('prefix'), get_option('localedir'))

# Configuration data
conf = configuration_data()
conf.set('PYTHON', python3.path())
conf.set('VERSION', meson.project_version())
conf.set('LOCALEDIR', localedir)
conf.set('PKGDATADIR', pkgdatadir)

# Add subdirectories
subdir('data')
subdir('src')
subdir('po')

# Install Python modules
python3.install_sources([
  'src/__init__.py',
  'src/__main__.py',
  'src/main.py',
  'src/main_window.py',
  'src/models.py',
  'src/preferences.py',
  'src/server.py',
  'src/tunnel.py',
  'src/request_row.py',
  'src/error_handler.py',
  'src/error_dialog.py',
  'src/input_sanitizer.py',
  'src/_version.py',
], subdir: 'echo')

# Post-install script
gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
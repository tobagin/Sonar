# Configure version file
configure_file(
  input: '_version.py.in',
  output: '_version.py',
  configuration: {
    'VERSION': meson.project_version()
  },
  install: true,
  install_dir: moduledir
)
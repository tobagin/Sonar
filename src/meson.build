# Configure and install version file
version_py = configure_file(
  input: '_version.py.in',
  output: '_version.py',
  configuration: {
    'VERSION': meson.project_version()
  },
  install: true,
  install_dir: python3.get_install_dir() / 'sonar'
)
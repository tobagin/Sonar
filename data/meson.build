# Desktop file
desktop_file = i18n.merge_file(
  input: 'io.github.tobagin.sonar.desktop.in',
  output: 'io.github.tobagin.sonar.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

# Validate desktop file
desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
endif

# AppData file - first configure variables, then merge translations
appdata_configured = configure_file(
  input: 'io.github.tobagin.sonar.appdata.xml.in',
  output: 'io.github.tobagin.sonar.appdata.xml.configured',
  configuration: {
    'VERSION': meson.project_version(),
    'DATE': '2025-07-18'
  }
)

appdata_file = i18n.merge_file(
  input: appdata_configured,
  output: 'io.github.tobagin.sonar.appdata.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)

# Validate appdata file
appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appdata file', appstream_util,
    args: ['validate', appdata_file]
  )
endif

# GSettings schema
install_data('io.github.tobagin.sonar.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

# Blueprint files
blueprints = [
  'ui/main_window.blp',
  'ui/request_row.blp',
]

# Use blueprint compiler from main meson.build

# Compile blueprint files to UI files
ui_files = []
foreach blueprint : blueprints
  ui_file = blueprint.replace('.blp', '.ui').replace('ui/', '')
  ui_files += custom_target(
    ui_file,
    input: blueprint,
    output: ui_file,
    command: [blueprint_compiler, 'compile', '--output', '@OUTPUT@', '@INPUT@'],
    install: false,
  )
endforeach

# Generate GResource file
resources = gnome.compile_resources(
  'sonar-resources',
  'resources/sonar.gresource.xml',
  dependencies: ui_files,
  source_dir: meson.current_build_dir(),
  gresource_bundle: true,
  install: true,
  install_dir: join_paths(get_option('datadir'), 'sonar')
)

# Icons
subdir('icons')

# Install compiled executable
configure_file(
  input: join_paths('..', 'src', 'sonar.in'),
  output: 'sonar',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)
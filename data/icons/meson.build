# Install application icons
icon_sizes = ['16x16', '32x32', '48x48', '64x64', '128x128', '256x256', '512x512']

foreach size : icon_sizes
  install_data(
    'hicolor' / size / 'apps' / 'io.github.tobagin.echo.png',
    install_dir: join_paths(get_option('datadir'), 'icons', 'hicolor', size, 'apps')
  )
endforeach

install_data(
  'hicolor/scalable/apps/io.github.tobagin.echo.png',
  install_dir: join_paths(get_option('datadir'), 'icons', 'hicolor', 'scalable', 'apps')
)

install_data(
  'hicolor/symbolic/apps/io.github.tobagin.echo-symbolic.svg',
  install_dir: join_paths(get_option('datadir'), 'icons', 'hicolor', 'symbolic', 'apps')
)
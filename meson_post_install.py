#!/usr/bin/env python3
"""
Post-install script for Echo.
"""

import os
import subprocess
import sys


def main():
    """Run post-install tasks."""
    datadir = sys.argv[1] if len(sys.argv) > 1 else '/usr/share'
    
    # Don't run post-install hooks during Flatpak build
    if os.environ.get('FLATPAK_ID'):
        return
    
    print('Updating icon cache...')
    try:
        subprocess.run([
            'gtk-update-icon-cache', '-qtf',
            os.path.join(datadir, 'icons', 'hicolor')
        ], check=True)
    except subprocess.CalledProcessError:
        print('Warning: Failed to update icon cache')
    
    print('Updating desktop database...')
    try:
        subprocess.run([
            'update-desktop-database', '-q',
            os.path.join(datadir, 'applications')
        ], check=True)
    except subprocess.CalledProcessError:
        print('Warning: Failed to update desktop database')
    
    print('Compiling GSettings schemas...')
    try:
        subprocess.run([
            'glib-compile-schemas',
            os.path.join(datadir, 'glib-2.0', 'schemas')
        ], check=True)
    except subprocess.CalledProcessError:
        print('Warning: Failed to compile GSettings schemas')


if __name__ == '__main__':
    main()
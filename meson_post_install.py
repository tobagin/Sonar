#!/usr/bin/env python3
"""
Post-install script for Sonar.
"""

import logging
import os
import subprocess
import sys


def main():
    """Run post-install tasks."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    datadir = sys.argv[1] if len(sys.argv) > 1 else '/usr/share'
    
    # Don't run post-install hooks during Flatpak build
    if os.environ.get('FLATPAK_ID'):
        logger.info('Skipping post-install hooks during Flatpak build')
        return
    
    logger.info('Updating icon cache...')
    try:
        subprocess.run([
            'gtk-update-icon-cache', '-qtf',
            os.path.join(datadir, 'icons', 'hicolor')
        ], check=True)
    except subprocess.CalledProcessError:
        logger.warning('Failed to update icon cache')
    
    logger.info('Updating desktop database...')
    try:
        subprocess.run([
            'update-desktop-database', '-q',
            os.path.join(datadir, 'applications')
        ], check=True)
    except subprocess.CalledProcessError:
        logger.warning('Failed to update desktop database')
    
    logger.info('Compiling GSettings schemas...')
    try:
        subprocess.run([
            'glib-compile-schemas',
            os.path.join(datadir, 'glib-2.0', 'schemas')
        ], check=True)
    except subprocess.CalledProcessError:
        logger.warning('Failed to compile GSettings schemas')


if __name__ == '__main__':
    main()
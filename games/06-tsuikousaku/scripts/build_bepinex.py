"""Sixth-game bootstrap entry; translation build awaits hook and text review."""
import sys
if __name__ == '__main__':
    if '--probe' not in sys.argv:
        raise SystemExit('Sixth-game translation build is not ready. Use probe for offline bootstrap validation.')
    from build_probe import main
    main()

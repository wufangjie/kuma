from _travel import Travel, BaseScreen, main
from PyQt5.QtCore import pyqtSignal, QThread


from AppKit import NSEvent #, NSKeyUp, NSBundle, NSSystemDefined
import Quartz

import logging

logger = logging.getLogger(__name__)


class DarwinScreen(BaseScreen):
    def get_windows(self):
        # TODO:
        return []

    def activate_window(self, hw):
        # TODO: maybe use open -a to activate application
        pass

    def close_window(self, hw):
        # TODO: maybe see CMD + w
        pass


def run_event_loop(keyboard_tap_callback):
    logger.info("try to load mac hotkey event loop")

    # Set up a tap, with type of tap, location, options and event mask
    tap = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap,  # Session level is enough for our needs
        Quartz.kCGHeadInsertEventTap,  # Insert wherever, we do not filter
        Quartz.kCGEventTapOptionDefault,
        # Quartz.CGEventMaskBit(NSSystemDefined), # for media keys
        Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp),
        keyboard_tap_callback,
        None
    )

    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
    Quartz.CFRunLoopAddSource(
        Quartz.CFRunLoopGetCurrent(),
        run_loop_source,
        Quartz.kCFRunLoopDefaultMode
    )
    # Enable the tap
    Quartz.CGEventTapEnable(tap, True)
    # and run! This won't return until we exit or are terminated.
    Quartz.CFRunLoopRun()
    logger.error('Mac hotkey event loop exit')


def parse_hotkey_mode(text, default=0x40001):
    return {'alt': 0x80020,
            'ctrl': 0x40001,
            'shift': 0x20002}.get(text.lower(), default)



if __name__ == '__main__':

    kuma = Travel(DarwinScreen())
    key = int(kuma.options.get('hotkey_darwin', 41))
    mod = parse_hotkey_mode(kuma.options.get('hotkey_mode', ''))

    class Listen(QThread):
        _show = pyqtSignal(name='show')

        def run(self):
            run_event_loop(self.keyboard_tap_callback)

        def keyboard_tap_callback(self, proxy, type_, event, refcon):
            key_event = NSEvent.eventWithCGEvent_(event)
            if key_event is not None:
                # print(key_event) # press keys to see flags and keyCode
                # breakpoint() # for debug
                if ((key_event.modifierFlags() & mod) == mod
                    and key_event.keyCode() == key):
                    # print("Catched kuma")
                    if not kuma.running:
                        logger.error('Kuma is not running, this should never happen?')
                        raise Exception("never happen?")
                    self._show.emit()
            return event

    main(kuma, Listen())

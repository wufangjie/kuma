from PyQt5.QtCore import pyqtSignal, QThread
from _travel import Travel, BaseScreen, main
from utils import run_script

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
    # logger.info("try to load mac hotkey event loop")

    for t in [Quartz.kCGEventKeyDown, Quartz.kCGEventFlagsChanged]:
        # Set up a tap, with type of tap, location, options and event mask
        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,  # Session level is enough for our needs
            Quartz.kCGHeadInsertEventTap,  # Insert wherever, we do not filter
            Quartz.kCGEventTapOptionDefault,
            # Quartz.CGEventMaskBit(NSSystemDefined), # for media keys
            Quartz.CGEventMaskBit(t),
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


def print_keycode():
    def keyboard_tap_print_callback(proxy, type_, event, refcon):
        key_event = NSEvent.eventWithCGEvent_(event)
        if key_event is not None:
            print(key_event) # press keys to see flags and keyCode
            # breakpoint() # for debug
        return event
    run_event_loop(keyboard_tap_print_callback)


def parse_hotkey_mode(text, default=0x40001):
    return {'alt': 0x80020,
            'ctrl': 0x40001,
            'shift': 0x20002}.get(text.lower(), default)


if __name__ == '__main__':

    kuma = Travel(DarwinScreen())
    key_kuma = int(kuma.options.get('hotkey_darwin', 41))
    mod_kuma = parse_hotkey_mode(kuma.options.get('hotkey_mode', ''))
    mod_alt = parse_hotkey_mode('alt')

    class Listen(QThread):
        _show = pyqtSignal(name='show')

        def run(self):
            run_event_loop(self.keyboard_tap_callback)

        def keyboard_tap_callback(self, proxy, type_, event, refcon):
            key_event = NSEvent.eventWithCGEvent_(event)
            if key_event is not None:
                # print(key_event) # press keys to see flags and keyCode
                # breakpoint() # for debug
                mod = key_event.modifierFlags()
                key = key_event.keyCode()
                if (mod & mod_kuma) == mod_kuma and key == key_kuma:
                    self._show.emit()
                elif (mod & mod_alt) == mod_alt:
                    if key == 19:
                        run_script("open -a emacs")
                    elif key == 20:
                        run_script("open -a safari")
            return event

    main(kuma, Listen())

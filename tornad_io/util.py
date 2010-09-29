from tornado import ioloop

import time
import logging

class PeriodicCallback(object):
    """Schedules the given callback to be called periodically.

    The callback is called every callback_time milliseconds.
    """
    def __init__(self, callback, callback_time, io_loop=None):
        self.callback = callback
        self.callback_time = callback_time
        self.io_loop = io_loop or ioloop.IOLoop.instance()
        self._running = False

    def start(self):
        self._running = True
        timeout = time.time() + self.callback_time / 1000.0
        self._timeout = self.io_loop.add_timeout(timeout, self._run)

    def stop(self):
        logging.debug("Stop.")
        self._running = False
        logging.debug("[stop] Running ? %s." % self._running)
        #self.io_loop.remove_timeout(self._timeout)

    def _run(self):
        if not self._running: return
        logging.debug("Running ? %s." % self._running)
        try:
            self.callback()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            logging.error("Error in periodic callback", exc_info=True)
        self.start()

#!/usr/bin/env python

import time
import psphere.client

class Client:
    """
    Holds a psphere.client.Client object.
    """
    def __init__(self):
        self.client = psphere.client.Client()

class Tasker:
    """
    Launches a task and watches it for completion.  Attempts to print
    possibly-useful diagnostics to the standard output and/or standard
    error along the way.
    """
    def task(self, vm, task):
        """
        A method to launch a task, run it, and watch its progress.
        """
        while task.info.state in ['queued', 'running']:
            print '.'
            time.sleep(5)
            task.update()
        if task.info.state == 'success':
            elapsed = task.info.completeTime - task.info.startTime
            print 'Task completed successfully in %s seconds' % (elapsed.seconds)
        elif task.info.state == 'error':
            print 'Task ended in error'
            try:
                print task.info.error.localizedMessage
                print task.info.error.fault.text
            except AttributeError:
                raise Exception('No error message available')
        else:
            raise Exception('Task in unknown state %s' % (task.info.state))


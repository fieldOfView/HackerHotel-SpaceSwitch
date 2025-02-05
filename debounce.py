from threading import Timer


def debounce(wait):
    """ Decorator that will postpone a functions
        execution until after wait seconds
        have elapsed since the last time it was invoked. """
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)
            try:
                debounced.timer.cancel()
            except(AttributeError):
                pass
            debounced.timer = Timer(wait, call_it)
            debounced.timer.start()
        return debounced
    return decorator
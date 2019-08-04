import datetime as dt


class datetime(dt.datetime):
    """The standard datetime class with the added support for the % and //
    operators.
    Refer to https://gist.github.com/treyhunner/6218526

    Example
    -------

    >>> from datetime_modulo import datetime
    >>> from datetime import timedelta
    >>> d = datetime.now()
    >>> d
    datetime(2016, 4, 15, 18, 16, 37, 684181)
    >>> d % timedelta(seconds=60)
    datetime.timedelta(0, 37, 684181)
    >>> d // timedelta(seconds=60)
    datetime.datetime(2016, 4, 15, 18, 16)
    >>> d % timedelta(minutes=15)
    datetime.timedelta(0, 97, 684181)
    >>> d // timedelta(minutes=15)
    datetime.datetime(2016, 4, 15, 18, 15)
    """

    def __divmod__(self, delta):
        seconds = int(
            (self -
             dt.datetime.min.replace(
                 tzinfo=self.tzinfo)).total_seconds())
        remainder = dt.timedelta(
            seconds=seconds % delta.total_seconds(),
            microseconds=self.microsecond,
            )
        quotient = self - remainder
        return quotient, remainder

    def __floordiv__(self, delta):
        return divmod(self, delta)[0]

    def __mod__(self, delta):
        return divmod(self, delta)[1]


if __name__ == '__main__':
    period = 1

    t = datetime.now()
    rt = t % dt.timedelta(hours=period)
    wait = dt.timedelta(hours=period) - rt

    print(t)
    print(rt)
    print(wait.total_seconds())

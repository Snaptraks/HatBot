from datetime import timedelta


zero_width_space = '\U0000200B'


def pretty_print_timedelta(delta: timedelta):
    seconds = int(delta.total_seconds())
    days, seconds = divmod(seconds, 3600 * 24)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    out_str = ''
    if seconds > 0:
        out_str = f'{seconds}s {out_str}'

    if minutes > 0:
        out_str = f'{minutes}m {out_str}'

    if hours > 0:
        out_str = f'{hours}h {out_str}'

    if abs(days) > 0:
        out_str = f'{days}d {out_str}'

    return out_str.strip()

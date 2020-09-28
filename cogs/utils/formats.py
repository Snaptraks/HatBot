from datetime import timedelta


zero_width_space = '\U0000200B'


def pretty_print_timedelta(delta: timedelta):
    seconds = int(delta.total_seconds())
    days, seconds = divmod(seconds, 3600 * 24)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    time_string = ""
    if seconds > 0:
        time_string = f"{seconds}s {time_string}"

    if minutes > 0:
        time_string = f"{minutes}m {time_string}"

    if hours > 0:
        time_string = f"{hours}h {time_string}"

    if abs(days) > 0:
        time_string = f"{days}d {time_string}"

    if time_string == "":
        time_string = "less than a second"

    return time_string.strip()

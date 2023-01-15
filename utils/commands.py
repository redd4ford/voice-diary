from utils import DateFormatter


class Commands:
    DELETE_REGEX = rf'^/d_(\d{len(DateFormatter.get_current_timestamp())})$'

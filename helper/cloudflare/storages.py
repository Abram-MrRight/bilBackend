from storages.backends.s3 import S3Storage

class CloudflareStorage(S3Storage):
    pass


class StaticFileStorage(CloudflareStorage):
    """
    For staticfiles
    """

    location = "static"
    default_acl = "public-read"


class MediaFileStorage(CloudflareStorage):
    """
    For general uploads
    """

    location = "media"
    default_acl = "public-read"
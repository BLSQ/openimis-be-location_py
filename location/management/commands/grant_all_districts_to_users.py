import logging

from django.core.management import BaseCommand

from core.models import InteractiveUser
from location.models import Location, UserDistrict


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "This command will create a UserDistrict for each active user and each existing District."

    def handle(self, *args, **options):
        logger.info("*** STARTING TO GRANT ALL ACTIVE USERS ACCESS TO ALL DISTRICTS ***")
        district_ids_set = set(Location.objects.filter(validity_to__isnull=True, type="D")
                                               .values_list("id", flat=True))
        active_users = (InteractiveUser.objects.filter(validity_to__isnull=True)
                                               .prefetch_related("userdistrict_set"))
        from core import datetime
        now = datetime.datetime.now()
        audit_user_id = -1

        total_created = 0

        logger.info(f"Districts found: {len(district_ids_set)} - {district_ids_set}")
        logger.info(f"Active users found: {len(active_users)}")

        for user in active_users:
            user_districts_set = set(user.userdistrict_set.filter(validity_to__isnull=True)
                                                          .values_list("location_id", flat=True))
            logger.info(f"Processing user {user.id} - user districts {user_districts_set}")
            diff_ids = district_ids_set - user_districts_set
            for missing_district_id in diff_ids:
                logger.info(f"Creating new UserDistrict for user {user.id} - district {missing_district_id}")
                UserDistrict.objects.create(
                    location_id=missing_district_id,
                    user_id=user.id,
                    audit_user_id=audit_user_id,
                    validity_from=now
                )
                total_created += 1

        logger.info("**************************************")
        logger.info(f"Total created: {total_created}")

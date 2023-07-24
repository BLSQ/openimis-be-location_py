import os
import csv

from django.core.management import BaseCommand

from core.models import InteractiveUser
from location.models import Location, UserDistrict

LOCATION_TYPE_REGION = "R"
LOCATION_TYPE_DISTRICT = "D"
LOCATION_TYPE_WARD = "W"
LOCATION_TYPE_VILLAGE = "V"
LOCATION_TYPES = [LOCATION_TYPE_REGION, LOCATION_TYPE_DISTRICT, LOCATION_TYPE_WARD, LOCATION_TYPE_VILLAGE]


def update_location(location: Location, new_code: str, new_name: str):
    from core import datetime

    location.save_history()
    location.name = new_name
    location.code = new_code
    location.audit_user_id = -1
    location.validity_from = datetime.datetime.now()
    location.save()


class Command(BaseCommand):
    help = "This command will import Locations from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_location",
                            nargs=1,
                            type=str,
                            help="Absolute path to the Location CSV file")
        parser.add_argument('-t',
                            '--type',
                            type=str,
                            dest='type',
                            required=True,
                            help=f'Location type; {LOCATION_TYPE_REGION}=Region, '
                                 f'{LOCATION_TYPE_DISTRICT}=District, '
                                 f'{LOCATION_TYPE_WARD}=Ward, '
                                 f'{LOCATION_TYPE_VILLAGE}=Village',
                            choices=LOCATION_TYPES)
        parser.add_argument('-u',
                            '--user_districts',
                            action='store_true',
                            dest='uds',
                            help='Automatically adds a new UserDistrict to the admin user if a new District is created',
        )

    def handle(self, *args, **options):
        file_location = options["csv_location"][0]
        if not os.path.isfile(file_location):
            print(f"Error - {file_location} is not a correct file path.")
        else:
            with open(file_location, mode='r', encoding='utf-8') as csv_file:

                total_rows = 0
                total_location_created = 0
                total_location_updated = 0
                total_ud_created = 0
                total_errors = 0

                location_type = options.get("type", None)
                add_uds = options["uds"]
                if add_uds:
                    admin = InteractiveUser.objects.filter(validity_to__isnull=True, login_name="Admin").first()

                print(f"**** Starting to import locations from {file_location} ***")

                csv_reader = csv.DictReader(csv_file, delimiter=',')
                for row in csv_reader:
                    total_rows += 1

                    location_name = row["name"].strip()
                    location_code = row["code"].strip()

                    if location_type != LOCATION_TYPE_REGION:
                        parent_code = row["parent_code"].strip()

                        parent_location = Location.objects.filter(
                            validity_to__isnull=True,
                            code=parent_code
                        ).first()
                        if not parent_location:
                            total_errors += 1
                            print(f"\t Line {total_rows} - Error: parent unknown - no code ({parent_code})")
                            continue
                    else:
                        parent_location = None

                    location, created = Location.objects.get_or_create(
                        validity_to=None,
                        type=location_type,
                        code=location_code,
                        name=location_name,
                        parent=parent_location,
                        defaults={
                            "audit_user_id": -1
                        }
                    )
                    if created:
                        print(f"\t Line {total_rows} - Location created")
                        total_location_created += 1
                        
                        if add_uds and location_type == LOCATION_TYPE_DISTRICT:
                            if admin:
                                UserDistrict.objects.create(
                                    audit_user_id=-1,
                                    user=admin,
                                    location=location,
                                )
                                total_ud_created += 1
                            else:
                                print(f"\Error during the UserDistrict creation - Admin couldn't be found")
                    else:
                        update_location(location, location_code, location_name)
                        total_location_updated += 1
                        print(f"\t Line {total_rows} - Location updated")

                print("-------------------------")
                print(f"Total received: {total_rows}")
                uds_string = f"{total_location_created} + {total_ud_created} UserDistrict(s) to the admin"
                print(f"Total created: {total_location_created if location_type != LOCATION_TYPE_DISTRICT else uds_string}")
                print(f"Total updated: {total_location_updated}")
                print(f"Total errors: {total_errors}\n")

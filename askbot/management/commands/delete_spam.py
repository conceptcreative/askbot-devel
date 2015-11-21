from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Delete forum spam'

    def handle(self, *args, **options):
        webmaster = User.objects.get(username='Webmaster')
        spammers = User.objects.filter(show_country=True).exclude(status='b')

        for spammer in spammers:
            print 'Blocking user:', spammer.username
            spammer.set_status('b')
            webmaster.delete_all_content_authored_by_user(spammer)


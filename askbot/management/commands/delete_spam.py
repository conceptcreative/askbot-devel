import datetime as dt
import mandrill

from askbot.conf import settings as askbot_settings

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from askbot.forms import EditUserEmailFeedsForm

class Command(BaseCommand):
    help = 'Delete forum spam'

    def handle(self, *args, **options):
        spammers = User.objects.filter(show_country=True).exclude(status='b')
        self.block_spammers(spammers)

        spammers = User.objects.filter(email__regex=r'^[a-zA-Z0-9]+\.[a-zA-Z0-9]+_[0-9]+@.*$').exclude(status='b')
        self.block_spammers(spammers)

        if 'check_emails' not in args:
            return

        client = mandrill.Mandrill(askbot_settings.MANDRILL_API_KEY)

        day = dt.timedelta(days=1)
        today = dt.date.today()
        yesterday = today - day

        msgs = client.messages.search(
            senders=['webmaster@usagrants.us'],
            date_from=str(yesterday),
            date_to=str(today),
            limit=1000
        )

        emails = [msg['email'] for msg in msgs if msg['state'] in ('bounced', 'rejected', 'spam')]
        emails = [email for email in emails if 'guest' not in emails]

        users = User.objects.filter(email__in=emails)

        for user in users:
            print 'Disabling emails for user:', user.username
            self.block_email(user)

    def block_email(self, user):
        EditUserEmailFeedsForm().reset().save(user, save_unbound=True)

    def block_spammers(self, spammers):
        webmaster = User.objects.get(username='Webmaster')

        for spammer in spammers:
            print 'Blocking user:', spammer.username
            self.block_email(spammer)
            spammer.set_status('b')
            webmaster.delete_all_content_authored_by_user(spammer)

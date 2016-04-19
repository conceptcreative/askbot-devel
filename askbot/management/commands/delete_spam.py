import datetime as dt
import requests
from requests.auth import HTTPBasicAuth
import time

from askbot.conf import settings as askbot_settings

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from askbot.forms import EditUserEmailFeedsForm

class Command(BaseCommand):
    help = 'Delete forum spam'

    def handle(self, *args, **options):
        spammers = User.objects.filter(show_country=True).exclude(status='b')
        self.block_spammers(spammers)

        spammers = User.objects.filter(email__regex=r'^[a-zA-Z0-9]+\.[a-zA-Z0-9]+_[0-9]+@.*$').exclude(status='b')
        self.block_spammers(spammers)

        spammers = User.objects.filter(
            username__regex='^' + '.' * 10 + '$',
            email__regex=r'.*@.*\..*\..*'
        ).exclude(status='b')
        self.block_spammers(spammers)

        if 'check_emails' not in args:
            return

        url = (
            'https://api.sendgrid.com'
            '/v3/suppression/{kind}'
            '?start_time={start_time}'
            '&end_time={end_time}'
            '&limit=100&offset=0'
        )
        auth = HTTPBasicAuth('grantjenks', askbot_settings.MANDRILL_API_KEY)
        suppressions = ['blocks', 'bounces', 'invalid_emails', 'spam_reports']
        end_time = int(time.time())
        start_time = int(end_time - 3 * 24 * 60 * 60)
        params = {'start_time': start_time, 'end_time': end_time}

        emails = []

        for kind in suppressions:
            params['kind'] = kind
            full_url = url.format(**params)
            resp = requests.get(full_url, auth=auth)
            emails.extend(result['email'] for result in resp.json())
            time.sleep(1)

        emails = [email for email in emails if 'guest' not in emails]

        users = User.objects.filter(email__in=emails).exclude(status='b')

        for user in users:
            print 'Disabling emails for user:', user.username, user.email
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

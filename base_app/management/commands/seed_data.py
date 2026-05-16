from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from offers_app.models import Offer, OfferDetail
from orders_app.models import Order
from profiles_app.models import UserProfile
from reviews_app.models import Review


class Command(BaseCommand):
    help = 'Seed database with demo data'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete all existing data first')

    def handle(self, *args, **options):
        if options['clear']:
            self._clear()

        biz1 = self._make_user('kevin_b', 'kevin@coderr.de', 'Kevin Braun', 'business')
        biz2 = self._make_user('anna_b', 'anna@coderr.de', 'Anna Weber', 'business')
        cust1 = self._make_user('max_k', 'max@coderr.de', 'Max Keller', 'customer')
        cust2 = self._make_user('lisa_m', 'lisa@coderr.de', 'Lisa Müller', 'customer')
        guest_customer = self._make_user('andrey', 'andrey@coderr.de', 'Andrey Guest', 'customer', password='asdasd')
        guest_business = self._make_user('kevin', 'kevin.guest@coderr.de', 'Kevin Guest', 'business', password='asdasd24')

        self._update_profile(biz1, location='Berlin', description='Full-Stack Developer mit 8 Jahren Erfahrung.', working_hours='Mo–Fr 9–18 Uhr')
        self._update_profile(biz2, location='München', description='UI/UX Designerin & Webentwicklerin.', working_hours='Mo–Do 10–17 Uhr')

        offer1 = self._make_offer(biz1, 'Professionelle Website-Entwicklung',
                                  'Ich entwickle moderne, responsive Websites.')
        self._make_details(offer1, [
            ('basic',    'Einfache Landing Page',  1,  5,  '299.00', ['1 Seite', 'Responsive Design', 'Kontaktformular']),
            ('standard', 'Business Website',       3, 10,  '799.00', ['5 Seiten', 'SEO-Optimierung', 'CMS-Integration', 'Responsive Design']),
            ('premium',  'Enterprise Webapp',      5, 20, '1999.00', ['Unbegrenzte Seiten', 'Custom Backend', 'API-Integration', 'Hosting-Setup']),
        ])

        offer2 = self._make_offer(biz1, 'React / Django REST API',
                                  'Skalierbare REST-APIs und React-Frontends.')
        self._make_details(offer2, [
            ('basic',    'Simple CRUD API',        1,  7,  '349.00', ['3 Endpunkte', 'Token-Auth', 'Dokumentation']),
            ('standard', 'REST API mit Auth',      3, 14,  '899.00', ['10 Endpunkte', 'JWT-Auth', 'Tests', 'Swagger-Docs']),
            ('premium',  'Full-Stack Applikation', 5, 28, '2499.00', ['Unbegrenzte Endpunkte', 'WebSockets', 'CI/CD', 'Docker']),
        ])

        offer3 = self._make_offer(biz2, 'UI/UX Design & Figma Prototyp',
                                  'Nutzerzentriertes Design für Web und Mobile.')
        self._make_details(offer3, [
            ('basic',    'Wireframes',        0,  3,  '199.00', ['5 Screens', 'Wireframes', 'Farbkonzept']),
            ('standard', 'Figma Prototyp',   2,  7,  '599.00', ['10 Screens', 'Klickbarer Prototyp', 'Design-System']),
            ('premium',  'Full Design Kit',  3, 14, '1299.00', ['Unbegrenzte Screens', 'Animationen', 'Entwickler-Handoff', 'Design-System']),
        ])

        detail_for_order = offer1.details.get(offer_type='standard')
        o1 = self._make_order(cust1, biz1, detail_for_order, status='completed')
        o2 = self._make_order(cust2, biz1, offer1.details.get(offer_type='basic'), status='in_progress')
        self._make_order(cust1, biz2, offer3.details.get(offer_type='standard'), status='in_progress')

        self._make_review(cust1, biz1, 5, 'Absolute Profi-Arbeit! Die Website wurde pünktlich und in Top-Qualität geliefert.')
        self._make_review(cust2, biz1, 4, 'Sehr gute Kommunikation, kleines Timing-Problem aber insgesamt sehr zufrieden.')
        self._make_review(cust1, biz2, 5, 'Fantastisches Design! Anna hat genau verstanden, was ich wollte.')

        self.stdout.write(self.style.SUCCESS('Seed erfolgreich!\n'))
        self.stdout.write('Accounts (Passwort für alle: pass123!)\n')
        for username, role in [('kevin_b', 'Business'), ('anna_b', 'Business'), ('kevin', 'Guest-Biz'), ('max_k', 'Customer'), ('lisa_m', 'Customer'), ('andrey', 'Guest-Cust')]:
            u = User.objects.get(username=username)
            t = Token.objects.get(user=u)
            self.stdout.write(f'  {role:10} {username:10}  Token: {t.key}')

    def _clear(self):
        Review.objects.all().delete()
        Order.objects.all().delete()
        Offer.objects.all().delete()
        for username in ('kevin_b', 'anna_b', 'kevin', 'max_k', 'lisa_m', 'andrey'):
            User.objects.filter(username=username).delete()
        self.stdout.write('Alte Demo-Daten gelöscht.')

    def _make_user(self, username, email, full_name, profile_type, password='pass123!'):
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            first, *rest = full_name.split()
            user.first_name = first
            user.last_name = ' '.join(rest)
            user.set_password(password)
            user.save()
        UserProfile.objects.get_or_create(user=user, defaults={'type': profile_type})
        Token.objects.get_or_create(user=user)
        return user

    def _update_profile(self, user, **kwargs):
        UserProfile.objects.filter(user=user).update(**kwargs)

    def _make_offer(self, user, title, description):
        offer, _ = Offer.objects.get_or_create(user=user, title=title, defaults={'description': description})
        return offer

    def _make_details(self, offer, specs):
        for offer_type, title, revisions, delivery_time_in_days, price, features in specs:
            OfferDetail.objects.get_or_create(
                offer=offer, offer_type=offer_type,
                defaults=dict(title=title, revisions=revisions,
                              delivery_time_in_days=delivery_time_in_days, price=price, features=features),
            )

    def _make_order(self, customer, business, detail, status='in_progress'):
        order, _ = Order.objects.get_or_create(
            customer_user=customer, business_user=business, title=detail.title,
            defaults=dict(revisions=detail.revisions, delivery_time_in_days=detail.delivery_time_in_days,
                          price=detail.price, features=detail.features, offer_type=detail.offer_type, status=status),
        )
        return order

    def _make_review(self, reviewer, business_user, rating, description):
        Review.objects.get_or_create(
            reviewer=reviewer, business_user=business_user,
            defaults=dict(rating=rating, description=description),
        )

from ..Base import Base
from datadog import initialize, api
from . import u_logger as log
import time


class DataDog(Base):
    def __init__(self, *args):
        super().__init__(*args)

    def initialize_data_dog(self):
        """Initialize The DataDog Class for metrics."""
        initialize(api_key=self.ex.keys.datadog_api_key, app_key=self.ex.keys.datadog_app_key)

    def send_metrics(self):
        """Send metrics for all stats."""
        try:
            if self.ex.irene_cache_loaded:
                metric_info = self.get_metric_info()

                # set all per minute metrics to 0 since this is a 60 second loop.
                self.ex.cache.n_words_per_minute = 0
                self.ex.cache.commands_per_minute = 0
                self.ex.cache.bot_api_idol_calls = 0
                self.ex.cache.bot_api_translation_calls = 0
                self.ex.cache.messages_received_per_minute = 0
                self.ex.cache.errors_per_minute = 0
                self.ex.cache.wolfram_per_minute = 0
                self.ex.cache.urban_per_minute = 0
                for metric_name in metric_info:
                    try:
                        metric_value = metric_info.get(metric_name)
                        self.ex.u_data_dog.send_metric(metric_name, metric_value)
                    except Exception as e:
                        log.console(f"{e} (Exception)", method=self.send_metrics)
        except Exception as e:
            # loop appears to stop working after a while and no errors were recognized in log file
            # adding this try except to see if issue continues.
            log.console(f"{e} (Exception2", method=self.send_metrics)

    def send_metric(self, metric_name, value):
        """Send a metric value to DataDog."""
        # some values at 0 are important such as active games, this was put in place to make sure they are updated at 0.
        metrics_at_zero = ['bias_games', 'guessing_games', 'commands_per_minute', 'n_words_per_minute',
                           'bot_api_idol_calls', 'bot_api_translation_calls', 'messages_received_per_min',
                           'errors_per_minute', 'wolfram_per_minute', 'urban_per_minute']
        if metric_name in metrics_at_zero and not value:
            value = 0
        else:
            if not value:
                return
        if self.ex.test_bot or self.ex.dev_mode:
            metric_name = 'test_bot_' + metric_name
        else:
            metric_name = 'irene_' + metric_name
        api.Metric.send(metric=metric_name, points=[(time.time(), value)])

    def get_metric_info(self):
        """Retrieves metric info to send to datadog."""
        user_notifications = 0
        patron_count = 0
        mod_mail = 0
        bot_banned = 0
        active_user_reminders = 0
        for user in self.ex.cache.users.values():
            user_notifications += len(user.notifications)
            if user.patron:
                patron_count += 1
            if user.mod_mail_channel_id:
                mod_mail += 1
            if user.bot_banned:
                bot_banned += 1
            active_user_reminders += len(user.reminders)

        user_copy = self.ex.cache.users.copy()
        gg_filtered_enabled = len([user for user in user_copy.values() if user.gg_filter])

        metric_info = {}  # contains all final data.

        # we classify the metrics in 4 different ways (the keys)
        # this is to allow for quick classification of how we assess our data and have the entire metric system not
        # crash due to an error with getting a value (this metric info used to not send due to float infinity issues
        # with a specific metric).
        metric_in_detail = {
            'normal': {  # we already have the values stored and can use it instantly.
                'total_commands_used': self.ex.cache.total_used,
                'patrons': patron_count,
                'mod_mail': mod_mail,
                'banned_from_bot': bot_banned,
                'user_notifications': user_notifications,
                'session_commands_used': self.ex.cache.current_session,
                'commands_per_minute': self.ex.cache.commands_per_minute,
                'n_words_per_minute': self.ex.cache.n_words_per_minute,
                'bot_api_idol_calls': self.ex.cache.bot_api_idol_calls,
                'bot_api_translation_calls': self.ex.cache.bot_api_translation_calls,
                'messages_received_per_min': self.ex.cache.messages_received_per_minute,
                'errors_per_minute': self.ex.cache.errors_per_minute,
                'wolfram_per_minute': self.ex.cache.wolfram_per_minute,
                'urban_per_minute': self.ex.cache.urban_per_minute,
                'active_user_reminders': active_user_reminders,
                'gg_filter_enabled': gg_filtered_enabled
            },
            'length_needed': {  # we need the len() of the metrics.
                'bias_games': self.ex.cache.bias_games,
                'guessing_games': self.ex.cache.guessing_games,
                'custom_server_prefixes': self.ex.cache.server_prefixes,
                'logged_servers': self.ex.cache.logged_channels,
                # server count is based on discord.py guild cache which takes a large amount of time to load fully.
                # There may be inaccurate data points on a new instance of the bot due to the amount of
                # time that it takes.
                'server_count': self.ex.client.guilds,
                'welcome_messages': self.ex.cache.welcome_messages,
                'temp_channels': self.ex.cache.temp_channels,
                'amount_of_idols': self.ex.cache.idols,
                'amount_of_groups': self.ex.cache.groups,
                'channels_restricted': self.ex.cache.restricted_channels,
                'amount_of_bot_statuses': self.ex.cache.bot_statuses,
                'amount_of_custom_commands': self.ex.cache.custom_commands,
                'twitch_channels_followed': self.ex.cache.twitch_channels.keys() or [],
                'voice_clients': self.ex.wavelink.players or [],
                'channels_with_games_disabled': self.ex.cache.channels_with_disabled_games,
                'dead_image_cache': self.ex.cache.dead_image_cache,
                'user_objects': self.ex.cache.users,
                'welcome_roles': self.ex.cache.welcome_roles,
                'members_in_support_server': self.ex.cache.member_ids_in_support_server,
                'active_unscramble_games': self.ex.cache.unscramble_games,
                'channels_with_automatic_photos': self.ex.cache.send_idol_photos.keys(),
                'servers_using_self_assignable_roles': self.ex.cache.assignable_roles.keys() or []
            },
            'method_call': {  # we need to call a custom method to get the value.
                'discord_ping': self.ex.get_ping
            },
            'sum_length': {  # need to sum a list after getting the len()
                'text_channels_following_twitch': self.ex.cache.twitch_channels.values(),
                'playing_cards': self.ex.cache.playing_cards.values(),

                'photos_sent_automatically': self.ex.cache.send_idol_photos.values(),
                'total_amount_of_self_assignable_roles': self.ex.cache.assignable_roles.values()
            }

        }

        normal_data = metric_in_detail.get("normal")
        for key, value in normal_data.items():
            try:
                metric_info[key] = value
            except Exception as e:
                log.console(f"{e} (Exception) - Failed to set key of normal datadog value {key} - {value}.",
                            method=self.get_metric_info)

        length_data = metric_in_detail.get("length_needed")
        for key, iterable in length_data.items():
            try:
                metric_info[key] = len(iterable)
            except Exception as e:
                log.console(f"{e} (Exception) - Failed to set key of iterable datadog value {key} - {iterable}.",
                            method=self.get_metric_info)

        custom_method_call = metric_in_detail.get("method_call")
        for key, method in custom_method_call.items():
            try:
                metric_info[key] = method()
            except Exception as e:
                log.console(f"{e} (Exception) - Failed to set key of method datadog value {key} - {method}.",
                            method=self.get_metric_info)

        sum_length_data = metric_in_detail.get("sum_length")
        for key, iterable in sum_length_data.items():
            try:
                if key == "total_amount_of_self_assignable_roles":
                    metric_info[key] = sum(len(x.get('roles') or []) for x in iterable)
                    continue
                metric_info[key] = sum(len(x) for x in iterable)
            except Exception as e:
                log.console(f"{e} (Exception) - Failed to set key of sum_iterable datadog value {key} - {iterable}.",
                            method=self.get_metric_info)

        return metric_info

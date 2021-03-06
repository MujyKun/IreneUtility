from ..Base import Base
from . import u_logger as log
import re
import pytz
import parsedatetime
import locale
import datetime
import random


# noinspection PyBroadException,PyPep8
class Reminder(Base):
    def __init__(self, *args):
        super().__init__(*args)

    @staticmethod
    async def determine_time_type(user_input):
        """Determine if time is relative time or absolute time
        relative time: remind me to _____ in 6 days
        absolute time: remind me to _____ at 6PM"""
        # TODO: add "on", "tomorrow", and "tonight" as valid inputs

        in_index = user_input.rfind(" in ")
        at_index = user_input.rfind(" at ")
        if in_index == at_index:
            return None, None
        if in_index > at_index:
            return True, in_index
        return False, at_index

    @staticmethod
    async def process_reminder_reason(user_input, cutoff_index):
        """Return the reminder reason that comes before in/at"""
        user_input = user_input[0: cutoff_index]
        user_words = user_input.split()
        if user_words[0].lower() == "me":
            user_words.pop(0)
        if user_words[0].lower() == "to":
            user_words.pop(0)
        return " ".join(user_words)

    async def process_reminder_time(self, user_input, type_index, is_relative_time, user_id):
        """Return the datetime of the reminder depending on the time format"""
        remind_time = user_input[type_index + len(" in "): len(user_input)]

        if is_relative_time:
            if await self.process_relative_time_input(remind_time) > 2 * 3.154e7:  # 2 years in seconds
                raise self.ex.exceptions.TooLarge
            return datetime.datetime.now() + datetime.timedelta(
                seconds=await self.process_relative_time_input(remind_time))

        return await self.process_absolute_time_input(remind_time, user_id)

    async def process_relative_time_input(self, time_input):
        """Returns the relative time of the input in seconds"""
        remind_time = 0  # in seconds
        input_elements = re.findall(r"[^\W\d_]+|\d+", time_input)

        if not any(alias in input_elements for alias in self.ex.cache.all_time_aliases):
            raise self.ex.exceptions.ImproperFormat

        for time_element in input_elements:
            try:
                int(time_element)
            except:
                # purposefully creating an error to locate which elements are words vs integers.
                for time_unit in self.ex.cache.time_units:
                    if time_element in time_unit[0]:
                        remind_time += time_unit[1] * int(input_elements[input_elements.index(time_element) - 1])
        return remind_time

    async def process_absolute_time_input(self, time_input, user_id):
        """Returns the absolute date time of the input"""
        user_timezone = await self.get_user_timezone(user_id)
        if not user_timezone:
            raise self.ex.exceptions.NoTimeZone
        cal = parsedatetime.Calendar()
        try:
            datetime_obj, _ = cal.parseDT(datetimeString=time_input, tzinfo=pytz.timezone(user_timezone))
            reminder_datetime = datetime_obj.astimezone(pytz.utc)
            return reminder_datetime
        except:
            raise self.ex.exceptions.ImproperFormat

    async def get_user_timezone(self, user_id):
        """Returns the user's timezone"""
        return (await self.ex.get_user(user_id)).timezone

    async def set_user_timezone(self, user_id, timezone):
        """Set user timezone"""
        user = await self.ex.get_user(user_id)
        if user.timezone:
            await self.ex.conn.execute("UPDATE reminders.timezones SET timezone = $1 WHERE userid = $2", timezone, user_id)
        else:
            await self.ex.conn.execute("INSERT INTO reminders.timezones(userid, timezone) VALUES ($1, $2)", user_id,
                                  timezone)
        user.timezone = timezone

    async def remove_user_timezone(self, user_id):
        """Remove user timezone"""
        try:
            user = await self.ex.get_user(user_id)
            user.timezone = None
            await self.ex.conn.execute("DELETE FROM reminders.timezones WHERE userid = $1", user_id)
        except:
            pass

    @staticmethod
    async def process_timezone_input(input_timezone, input_country_code=None):
        """Convert timezone abbreviation and country code to standard timezone name"""

        def now_tz_str(time_zone):
            return datetime.datetime.now(pytz.timezone(time_zone)).strftime("%Z")

        try:
            input_timezone = input_timezone.upper()
            input_country_code = input_country_code.upper()
        except:
            pass

        # Format if user input is in GMT offset format
        if any(char.isdigit() for char in input_timezone):
            try:
                timezone_offset = (re.findall(r"[+-]\d+", input_timezone))[0]
                timezone_sign = timezone_offset[0]
                timezone_value = timezone_offset[1:]
                # Swap GMT and UTC definitions, which are inverted of each other
                utc_offset = f"-{timezone_value}" if timezone_sign == "+" else f"+{timezone_value}"
                input_timezone = 'Etc/GMT' + utc_offset
            except:
                pass

        try:
            name_matching_timezones = set(common_tz for common_tz in pytz.common_timezones
                                          if now_tz_str(common_tz) == now_tz_str(input_timezone))
        except pytz.exceptions.UnknownTimeZoneError:
            name_matching_timezones = set(common_tz for common_tz in pytz.common_timezones
                                          if now_tz_str(common_tz) == input_timezone)
        except:
            name_matching_timezones = None

        # Find the timezones which share both same timezone input and the same country code
        if input_country_code:
            try:
                country_timezones = set(pytz.country_timezones[input_country_code])
                possible_timezones = name_matching_timezones & country_timezones
            except KeyError:  # Given country code is not a valid country code
                possible_timezones = name_matching_timezones
        else:  # Try to default to US timezone
            us_timezones = set(pytz.country_timezones['US'])
            possible_timezones = name_matching_timezones & us_timezones
            if not possible_timezones:
                possible_timezones = name_matching_timezones

        if not possible_timezones:
            return None

        return random.choice(list(possible_timezones))

    @staticmethod
    async def format_time(string_format, user_timezone, input_time: datetime.datetime = None):
        """ Format time according to the user timezone"""
        if not input_time:
            return datetime.datetime.now(pytz.timezone(user_timezone)).strftime(string_format)
        else:
            return input_time.astimezone(pytz.timezone(user_timezone)).strftime(string_format)

    async def get_locale_time(self, m_time, user_timezone=None):
        """ Return a string containing locale date format. For now, enforce all weekdays to be en_US format"""
        # Set locale to server locale
        weekday_format = '%a'
        date_format = '%x'
        time_format = '%I:%M:%S%p %Z'
        locale.setlocale(locale.LC_ALL, '')

        if not user_timezone:
            return m_time.strftime(f"{weekday_format} {date_format} {time_format}")

        # Use weekday format of server
        weekday = await self.format_time(weekday_format, user_timezone, m_time)

        # Format date according to the locale of the user
        user_locale = f"{(self.ex.cache.locale_by_timezone[user_timezone].replace('-', '_'))}.utf8"
        try:
            locale.setlocale(locale.LC_ALL, user_locale)  # Set to user locale
        except:
            locale.setlocale(locale.LC_ALL, 'en_US.utf8')
        locale_date = await self.format_time(date_format, user_timezone, m_time)
        locale.setlocale(locale.LC_ALL, '')  # Reset locale back to server locale

        # Use time format of the server
        local_time = await self.format_time(time_format, user_timezone, m_time)
        return f"{weekday} {locale_date} {local_time}"

    async def set_reminder(self, remind_reason, remind_time, user_id):
        """Add reminder date to cache and db."""
        await self.ex.conn.execute("INSERT INTO reminders.reminders(userid, reason, timestamp) VALUES ($1, $2, $3)",
                              user_id, remind_reason, remind_time)
        remind_id = self.ex.first_result(await self.ex.conn.fetchrow(
            "SELECT id FROM reminders.reminders WHERE userid=$1 AND reason=$2 AND timestamp=$3 ORDER BY id DESC",
            user_id, remind_reason, remind_time))
        user = await self.ex.get_user(user_id)
        remind_info = [remind_id, remind_reason, remind_time]
        if user.reminders:
            user.reminders.append(remind_info)
        else:
            user.reminders = [remind_info]

    async def get_reminders(self, user_id):
        """Get the reminders of a user"""
        return (await self.ex.get_user(user_id)).reminders

    async def remove_user_reminder(self, user_id, reminder_id):
        """Remove a reminder from the cache and the database."""
        try:
            # remove from cache
            reminders = await self.get_reminders(user_id)
            if reminders:
                for reminder in reminders:
                    current_reminder_id = reminder[0]
                    if current_reminder_id == reminder_id:
                        reminders.remove(reminder)
        except Exception as e:
            log.console(f"{e} (Exception)", method=self.remove_user_reminder)
        await self.ex.conn.execute("DELETE FROM reminders.reminders WHERE id = $1", reminder_id)


# self.ex.u_reminder = Reminder()

import re
import datetime

from billy.scrape.events import EventScraper, Event
from .scraper import InvalidHTTPSScraper

import lxml.html

class IAEventScraper(InvalidHTTPSScraper, EventScraper):
    jurisdiction = 'ia'

    def scrape(self, chamber, session):
        if chamber == 'other':
            return

        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=10)
        end_date = today + datetime.timedelta(days=10)

        if chamber == 'upper':
            chamber_abbrev = 'S'
        else:
            chamber_abbrev = 'H'

        url = ("http://www.legis.iowa.gov/committees/meetings/meetingsList"
               "Chamber?chamber=%s&bDate=%02d/%02d/"
               "%d&eDate=%02d/%02d/%d" % (chamber_abbrev,
                                          start_date.month,
                                          start_date.day,
                                          start_date.year,
                                          end_date.month,
                                          end_date.day,
                                          end_date.year))

        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)
        for link in page.xpath("//div[contains(@class, 'meetings')]/table[1]/tbody/tr[not(contains(@class, 'hidden'))]"):             
            comm = link.xpath("string(./td[2]/a[1]/text())").strip()
            desc = comm + " Committee Hearing"
            
            location = link.xpath("string(./td[3]/text())").strip()

            when = link.xpath("string(./td[1]/span[1]/text())").strip()
            
            if 'cancelled' in when.lower() or "upon" in when.lower():
                continue
            if "To Be Determined" in when:
                continue

            if 'AM' in when:
                when = when.split('AM')[0] + " AM"
            else:
                when = when.split('PM')[0] + " PM"

            junk = ['Reception']
            for key in junk:
                when = when.replace(key, '')

            when = re.sub("\s+", " ", when).strip()
            if "tbd" in when.lower():
                # OK. This is a partial date of some sort.
                when = datetime.datetime.strptime(
                    when,
                    "%m/%d/%Y TIME - TBD %p"
                )
            else:
                try:
                    when = datetime.datetime.strptime(when, "%m/%d/%Y %I:%M %p")
                except ValueError:
                    when = datetime.datetime.strptime(when, "%m/%d/%Y %I %p")

            event = Event(session, when, 'committee:meeting',
                          desc, location)
            event.add_source(url)
            event.add_participant('host', comm, 'committee', chamber=chamber)
            self.save_event(event)

# -*- coding: utf8 -*-

"""
Date and Time
"""

import time
from datetime import datetime, timedelta
import dateutil.parser
from mathics.core.expression import Expression, Real, Symbol, String, from_python
from mathics.builtin.base import Builtin, Predefined
from itertools import cycle

START_TIME = time.time()

TIME_INCREMENTS = {
    'Year':     (1, 0, 0, 0, 0, 0),
    'Quarter':  (0, 3, 0, 0, 0, 0),
    'Month':    (0, 1, 0, 0, 0, 0),
    'Week':     (0, 0, 7, 0, 0, 0),
    'Day':      (0, 0, 1, 0, 0, 0),
    'Hour':     (0, 0, 0, 1, 0, 0),
    'Minute':   (0, 0, 0, 0, 1, 0),
    'Second':   (0, 0, 0, 0, 0, 1),
}

#FIXME: Some of the formats are not supported by strftime/strptime (commented out)
DATE_STRING_FORMATS = {
    "Date": "%c",
    "DateShort": "%a %d %b %Y",
    "Time": "%X",
    "DateTime": "%c %X",
    "DateTimeShort": "%a %d %b %Y %X",
    "Year" : "%Y",
    "YearShort": "%y",
    #"QuarterName": "Quarter N",
    #"QuarterNameShort": "QN",
    #"Quarter": "",
    "MonthName": "%B",
    "MonthNameShort": "%b",
    #"MonthNameInitial": "%b",
    "Month": "%m",
    "MonthShort": "%m",
    "DayName": "%A",
    "DayNameShort": "%a",
    #"DayNameInitial": "%a",
    "Day": "%d",
    "DayShort": "%d",
    "Hour": "%H",               #TODO: Find system preferences (12/24 hour)
    "Hour12": "%I",
    "Hour24": "%H",
    "HourShort": "%H",
    "Hour12Short": "%I",
    "Hour24Short": "%H",
    "AMPM": "%p",
    #"AMPMLowerCase": "%p",
    "Minute": "%M",
    "MinuteShort": "%M",
    "Second": "%S",
    "SecondShort": "%S",
    "SecondExact": "%S.%f",
    #"Millisecond": "%f",
    #"MillisecondShort": "",
}


class Timing(Builtin):
    """
    <dl>
    <dt>'Timing[$expr$]'
      <dd>measures the processor time taken to evaluate $expr$.
      It returns a list containing the measured time in seconds and the result of the evaluation.
    </dl> 

    >> Timing[50!]
     = {..., 30414093201713378043612608166064768844377641568960512000000000000}
    >> Attributes[Timing]
     = {HoldAll, Protected}
    """
    
    attributes = ('HoldAll',)
    
    def apply(self, expr, evaluation):
        'Timing[expr_]'
        
        start = time.clock()
        result = expr.evaluate(evaluation)
        stop = time.clock()
        return Expression('List', Real(stop - start), result)


class AbsoluteTiming(Builtin):
    """
    <dl>
    <dt>'AbsoluteTiming[$expr$]'
      <dd>measures the actual time it takes to evaluate $expr$.
      It returns a list containing the measured time in seconds and the result of the evaluation.
    </dl> 

    >> AbsoluteTiming[50!]
     = {..., 30414093201713378043612608166064768844377641568960512000000000000}
    >> Attributes[AbsoluteTiming]
     = {HoldAll, Protected}
    """
    
    attributes = ('HoldAll',)
    
    def apply(self, expr, evaluation):
        'AbsoluteTiming[expr_]'
        
        start = time.time()
        result = expr.evaluate(evaluation)
        stop = time.time()
        return Expression('List', Real(stop - start), result)


class DateStringFormat(Predefined):
    """
    <dl>
    <dt>'$DateStringFormat'
      <dd>gives the format used for dates generated by DateString.
    </dl>

    >> $DateStringFormat
     = {DateTimeShort}
    """

    name = '$DateStringFormat'

    value = u'DateTimeShort'

    #TODO: Methods to change this

    def evaluate(self, evaluation):
        return Expression('List', String(self.value))


class _DateFormat(Builtin):
    def to_datelist(self, epochtime, evaluation):
        """ Converts date-time 'epochtime' to datelist """
        etime = epochtime.to_python()

        form_name = self.get_name()

        if isinstance(etime, float) or isinstance(etime, int):
            try:
                timestruct = time.gmtime(etime - 2208988800)
            except ValueError:
                #TODO: Fix arbitarily large times
                return

            datelist = list(timestruct[:5])
            datelist.append(timestruct[5] + etime % 1.)      # Hack to get seconds as float not int.
            return datelist

        if isinstance(etime, basestring):
            date = dateutil.parser.parse(etime.strip('"'))
            datelist = [date.year, date.month, date.day, date.hour, date.minute, date.second + 1e-06 * date.microsecond]
            return datelist

        if not isinstance(etime, list):
            evaluation.message(form_name, 'arg', etime)
            return

        if 1 <= len(etime) <= 6 and all((isinstance(val, float) and i>1) or isinstance(val, int) for i,val in enumerate(etime)):
            default_date = [1900, 1, 1, 0, 0, 0.]

            datelist = etime + default_date[len(etime):]
            prec_part, imprec_part = datelist[:2], datelist[2:]

            try:
                dtime = datetime(prec_part[0], prec_part[1], 1)
            except ValueError:
                #FIXME datetime is fairly easy to overlfow. 1 <= month <= 12 and some bounds on year too.
                evaluation.message(form_name, 'arg', epochtime)
                return

            tdelta = timedelta(days=imprec_part[0]-1, hours=imprec_part[1], minutes=imprec_part[2], seconds=imprec_part[3])
            dtime += tdelta
            datelist = [dtime.year, dtime.month, dtime.day, dtime.hour, dtime.minute, dtime.second + 1e-06 * dtime.microsecond]
            return datelist
            
        if len(etime) == 2:
            if isinstance(etime[0], basestring) and isinstance(etime[1], list) and all(isinstance(s, basestring) for s in etime[1]):
                is_spec = [str(s).strip('"') in DATE_STRING_FORMATS.keys() for s in etime[1]]
                etime[1] = map(lambda s: str(s).strip('"'), etime[1])

                if sum(is_spec) == len(is_spec):
                    forms = []
                    fields = [DATE_STRING_FORMATS[s] for s in etime[1]]
                    for sep in ['', ' ', '/', '-', '.', ',', ':']:
                        forms.append(sep.join(fields))
                else:
                    forms = ['']
                    for i,s in enumerate(etime[1]):
                        if is_spec[i]:
                            forms[0] += DATE_STRING_FORMATS[s]
                        else:
                            #TODO: Escape % signs?
                            forms[0] += s

                date = _Date()
                date.date = None
                for form in forms:
                    try:
                        date.date = datetime.strptime(str(etime[0]).strip('"'), form)
                        break
                    except ValueError:
                        pass

                if date.date is None:
                    evaluation.message(form_name, 'str', etime[0], etime[1])
                    return
                datelist = date.to_list()

                #If year is ambiguious, assume the current year
                if 'Year' not in etime[1] and 'YearShort' not in etime[1]:
                    datelist[0] = datetime.today().year

                return datelist

            else:
                evaluation.message(form_name, 'str', etime[0], etime[1])
                return

        evaluation.message(form_name, 'arg', epochtime)
        return


class DateList(_DateFormat):
    """
    <dl>
    <dt>'DateList[]'
      <dd>returns the current local time in the form {$year$, $month$, $day$, $hour$, $minute$, $second$}.
    <dt>'DateList[time_]'
      <dd>returns a formatted date for the number of seconds $time$ since epoch Jan 1 1900.
    <dt>'DateList[{y, m, d, h, m, s}]'
      <dd>converts an incomplete date list to the standard representation.
    </dl>

    >> DateList[0]
     = {1900, 1, 1, 0, 0, 0.}

    >> DateList[3155673600]
     = {2000, 1, 1, 0, 0, 0.}

    >> DateList[{2003, 5, 0.5, 0.1, 0.767}]
     = {2003, 4, 30, 12, 6, 46.02}

    >> DateList[{2012, 1, 300., 10, 0.}]
     = {2012, 10, 26, 10, 0, 0.}

    >> DateList[{"31/10/91", {"Day", "Month", "YearShort"}}]
     = {1991, 10, 31, 0, 0, 0.}

    >> DateList[{"31 10/91", {"Day", " ", "Month", "/", "YearShort"}}]
     = {1991, 10, 31, 0, 0, 0.}

    #strptime should ignore leading 0s
    #> DateList[{"6/6/91", {"Day", "Month", "YearShort"}}]
     = {1991, 6, 6, 0, 0, 0.}
    #> DateList[{"6/06/91", {"Day", "Month", "YearShort"}}]
     = {1991, 6, 6, 0, 0, 0.}
    #> DateList[{"06/06/91", {"Day", "Month", "YearShort"}}]
     = {1991, 6, 6, 0, 0, 0.}
    #> DateList[{"06/6/91", {"Day", "Month", "YearShort"}}]
     = {1991, 6, 6, 0, 0, 0.}

    # Current year assumed 
    #> DateList[{"5/18", {"Month", "Day"}}]
     = {2012, 5, 18, 0, 0, 0.}
    """

    rules = {
        'DateList[]': 'DateList[AbsoluteTime[]]',
    }

    messages = {
        'arg': 'Argument `1` cannot be intepreted as a date or time input.',
        'str': 'String `1` cannot be interpreted as a date in format `2`.',
    }

    def apply(self, epochtime, evaluation):
        '%(name)s[epochtime_]'
        datelist = self.to_datelist(epochtime, evaluation)

        if datelist is None:
            return

        return Expression('List', *datelist)


class DateString(_DateFormat):
    """
    <dl>
    <dt>'DateString[]'
      <dd>Returns the current local time and date as a string.
    <dt>'DateString[time]'
      <dd>Returns the date string of an AbsoluteTime.
    <dt>'DateString[{y, m, d, h, m, s}]'
      <dd>Returns the date string of a date list specification.

    The current date and time
    >> DateString[];

    >> DateString[{1991, 10, 31, 0, 0}, {"Day", " ", "MonthName", " ", "Year"}]
     = 31 October 1991

    >> DateString[{2007, 4, 15, 0}]
     = Sun 15 Apr 2007 00:00:00

    >> DateString[{1979, 3, 14}, {"DayName", "  ", "Month", "-", "YearShort"}]
     = Wednesday  03-79

    Non-integer values are accepted too
    >> DateString[{1991, 6, 6.5}]
     = Thu 6 Jun 1991 12:00:00

    # Check Leading 0
    #> DateString[{1979, 3, 14}, {"DayName", "  ", "MonthShort", "-", "YearShort"}]
     =  Wednesday  3-79

    #> DateString[{1979, 3, 4}]
     = Sun 4 Mar 1979 00:00:00
    
    #> DateString[{"DayName", "  ", "Month", "/", "YearShort"}]
     = ...

    #> DateString["2000-12-1", "Year"]
     = 2000

    # Assumed separators
    #> DateString[{"06/06/1991", {"Month", "Day", "Year"}}]
     = Thu 6 Jun 1991 00:00:00

    # Specified separators
    #> DateString[{"06/06/1991", {"Month", "/", "Day", "/", "Year"}}]
     = Thu 6 Jun 1991 00:00:00

    #> DateString[{"5/19"}]
     = 5/19
    """

    rules = {
        'DateString[]': 'DateString[DateList[], $DateStringFormat]',
        'DateString[epochtime_?(VectorQ[#1, NumericQ]&)]': 'DateString[epochtime, $DateStringFormat]',
        'DateString[epochtime_?NumericQ]': 'DateString[epochtime, $DateStringFormat]',
        'DateString[format_?(VectorQ[#1, StringQ]&)]': 'DateString[DateList[], format]',
        'DateString[epochtime_]': 'DateString[epochtime, $DateStringFormat]',
    }

    messages = {
        'arg': 'Argument `1` cannot be intepreted as a date or time input.',
        'fmt': '`1` is not a valid date format.',
    }

    attributes = ('ReadProtected',)

    def apply(self, epochtime, form, evaluation):
        'DateString[epochtime_, form_]'
        datelist = self.to_datelist(epochtime, evaluation)

        if datelist is None:
            return

        date = _Date(datelist=datelist)

        pyform = form.to_python()
        if not isinstance(pyform, list):
            pyform = [pyform]

        pyform = map(lambda x: x.strip('"'), pyform)

        if not all(isinstance(f, unicode) or isinstance(f, str) for f in pyform):
            evaluation.message('DateString', 'fmt', form)
            return

        datestrs = []
        for p in pyform:
            if str(p) in DATE_STRING_FORMATS.keys():
                #FIXME: Years 1900 before raise an error
                tmp = date.date.strftime(DATE_STRING_FORMATS[p])
                if str(p).endswith("Short") and str(p) != "YearShort":
                    if str(p) == "DateTimeShort":
                        tmp = tmp.split(' ')
                        tmp = ' '.join(map(lambda s: s.lstrip('0'), tmp[:-1])+[tmp[-1]])
                    else:
                        tmp = ' '.join(map(lambda s: s.lstrip('0'), tmp.split(' ')))
            else:
                tmp = str(p)

            datestrs.append(tmp)

        return from_python(''.join(datestrs))


class AbsoluteTime(_DateFormat):
    """
    <dl>
    <dt>'AbsoluteTime[]'
      <dd>Gives the local time in seconds since epoch Jan 1 1900.
    <dt>'AbsoluteTime["string"]'
      <dd>Gives the absolute time specification for a given date string.
    <dt>'AbsoluteTime[{y, m, d, h, m, s}]
      <dd>Gives the absolute time specification for a given date list.
    <dt>'AbsoluteTime[{"string",{$e1$, $e2$, ...}}]' 
      <dd>Gives the absolute time specification for a given date list with specified elements $ei$.
    </dl>

    >> AbsoluteTime[]
     = ...

    >> AbsoluteTime[{2000}]
     = 3155673600

    >> AbsoluteTime[{"01/02/03", {"Day", "Month", "YearShort"}}]
     = 3253046400

    >> AbsoluteTime["6 June 1991"]
     = 2885155200

    >> AbsoluteTime[{"6-6-91", {"Day", "Month", "YearShort"}}]
     = 2885155200

    #Mathematica Bug - Mathics gets it right
    #> AbsoluteTime[1000]
     = 1000
    """

    def apply_now(self, evaluation):
        'AbsoluteTime[]'
        return from_python(time.time() + 2208988800 - time.timezone)

    def apply_spec(self, epochtime, evaluation):
        'AbsoluteTime[epochtime_]'

        datelist = self.to_datelist(epochtime, evaluation)

        if datelist is None:
            return

        epoch = datetime(1900, 1, 1)
        date = _Date(datelist=datelist)
        tdelta = date.date - epoch
        if tdelta.microseconds == 0:
            return from_python(int(tdelta.total_seconds()))
        return from_python(tdelta.total_seconds())


class TimeZone(Predefined):
    """
    <dl>
    <dt>'$TimeZone'
      <dd> gives the current time zone.
    </dl>

    >> $TimeZone
     = ...
    """

    name = '$TimeZone'

    def evaluate(self, evaluation):
        return Real(-time.timezone / 3600.)


class TimeUsed(Builtin):
    """
    <dl>
    <dt>'TimeUsed[]'
      <dd>returns the total cpu time used for this session.
    </dl>
    
    >> TimeUsed[]
     = ...
    """

    def apply(self, evaluation):
        'TimeUsed[]'
        return Real(time.clock()) #TODO: Check this for windows


class SessionTime(Builtin):
    """
    <dl>
    <dt>'SessionTime[]'
      <dd>returns the total time since this session started.
    </dl>

    >> SessionTime[]
     = ...
    """
    def apply(self, evaluation):
        'SessionTime[]'
        return Real(time.time() - START_TIME)


class Pause(Builtin):
    """
    <dl>
    <dt>'Pause[n]'
      <dd>pauses for $n$ seconds.
    </dl>

    >> Pause[0.5]
    """

    messages = {
        'numnm': 'Non-negative machine-sized number expected at position 1 in `1`.',
    }

    def apply(self, n, evaluation):
        'Pause[n_]'
        sleeptime = n.to_python()
        if not (isinstance(sleeptime, int) or isinstance(sleeptime, float)) or sleeptime < 0:
            evaluation.message('Pause', 'numnm', Expression('Pause', n))
            return

        time.sleep(sleeptime)
        return Symbol('Null')


class _Date():
    def __init__(self, datelist = [], absolute=None, datestr=None):
        datelist += [1900, 1, 1, 0, 0, 0.][len(datelist):]
        self.date = datetime(
            datelist[0], datelist[1], datelist[2], datelist[3], datelist[4], 
            int(datelist[5]), int(1e6 * (datelist[5] % 1.)))
        if absolute is not None:
            self.date += timedelta(seconds=absolute)
        if datestr is not None:
            if absolute is not None:
                raise ValueError
            self.date = dateutil.parser.parse(datestr)
            

    def addself(self, timevec):
        years = self.date.year + timevec[0] + int((self.date.month + timevec[1]) / 12)
        months = (self.date.month + timevec[1]) % 12
        if months == 0:
            months += 12
            years -= 1
        self.date = datetime(years, months, self.date.day, self.date.hour, self.date.minute, self.date.second)
        tdelta = timedelta(days=timevec[2], hours=timevec[3], minutes=timevec[4], seconds=timevec[5])
        self.date += tdelta

    def to_list(self):
        return [self.date.year, self.date.month, self.date.day, self.date.hour, self.date.minute, self.date.second + 1e-6*self.date.microsecond]


class DatePlus(Builtin):
    """
    <dl>
    <dt>'DatePlus[date, n]'
      <dd>finds the date $n$ days after $date$.
    <dt>'DatePlus[date, {n, "unit"}]'
      <dd>finds the date $n$ units after $date$.
    <dt>'DatePlus[date, {{n1, "unit1"}, {n2, unit2}, ...}]'
      <dd>finds the date which is $n_i$ specified units after $date$.
    <dt>'DatePlus[n]'
      <dd>finds the date $n$ days after the current date.
    <dt>'DatePlus[offset]'
      <dd>finds the date which is offset from the current date.
    </dl>

    Add 73 days to Feb 5, 2010
    >> DatePlus[{2010, 2, 5}, 73]
     = {2010, 4, 19}

    Add 8 Weeks 1 day to March 16, 1999
    >> DatePlus[{2010, 2, 5}, {{8, "Week"}, {1, "Day"}}]
     = {2010, 4, 3}
    """

    rules = {
        'DatePlus[n_]': 'DatePlus[{DateList[][[1]], DateList[][[2]], DateList[][[3]]}, n]',
    }

    messages = {
        'date': 'Argument `1` cannot be interpreted as a date.',
        'inc': 'Argument `1` is not a time increment or a list of time increments.',
    }

    attributes = ('ReadProtected',)

    def apply(self, date, off, evaluation):
        'DatePlus[date_, off_]'
        
        # Process date
        pydate = date.to_python()
        if isinstance(pydate, list):
            date_prec = len(pydate)
            idate = _Date(datelist = pydate)
        elif isinstance(pydate, float) or isinstance(pydate, int):
            date_prec = 'absolute'
            idate = _Date(absolute = pydate)
        elif isinstance(pydate, basestring):
            date_prec = 'string'
            idate = _Date(datestr = pydate.strip('"'))
        else:
            evaluation.message('DatePlus', 'date', date)        
            return

        # Process offset
        pyoff = off.to_python()
        if isinstance(pyoff, float) or isinstance(pyoff, int):
            pyoff = [[pyoff, u'"Day"']]
        elif isinstance(pyoff, list) and len(pyoff) == 2 and isinstance(pyoff[1], unicode):
            pyoff = [pyoff]

        # Strip " marks
        pyoff = map(lambda x: [x[0], x[1].strip('"')], pyoff)

        if isinstance(pyoff, list) and all(len(o) == 2 and o[1] in TIME_INCREMENTS.keys() and (isinstance(o[0], float) or isinstance(o[0], int)) for o in pyoff):
            for o in pyoff:
                idate.addself([o[0] * TIME_INCREMENTS[o[1]][i] for i in range(6)])
        else:
            evaluation.message('DatePlus', 'inc', off) 
            return

        if isinstance(date_prec, int):
            result = Expression('List', *idate.to_list()[:date_prec])
        elif date_prec == 'absolute':
            result = Expression('AbsoluteTime', idate.to_list())
        elif date_prec == 'string':
            result = Expression('DateString', Expression('List', *idate.to_list()))

        return result


class DateDifference(Builtin):
    """
    <dl>
    <dt>'DateDifference[date1, date2]
      <dd> Difference between dates in days.
    <dt>'DateDifference[date1, date2, "unit"]
      <dd> Difference between dates in specified units.
    </dl>

    >> DateDifference[{2042, 1, 4}, {2057, 1, 1}]
     = 5476

    >> DateDifference[{1936, 8, 14}, {2000, 12, 1}, "Year"]
     = {64.3424657534, Year}

    >> DateDifference[{2010, 6, 1}, {2015, 1, 1}, "Hour"]
     = {40200, Hour}
    """
    
    rules = {
        'DateDifference[date1_, date2_]': """DateDifference[date1, date2, "Day"]""",
    }

    messages = {
        'date': 'Argument `1` cannot be interpreted as a date.',
        'inc': 'Argument `1` is not a time increment or a list of time increments.',
    }

    attributes = ('ReadProtected',)

    def apply(self, date1, date2, units, evaluation):
        'DateDifference[date1_, date2_, units_]'

        # Process dates
        pydate1, pydate2 = date1.to_python(), date2.to_python()

        if isinstance(pydate1, list):        # Date List
            idate = _Date(datelist = pydate1)
        elif isinstance(pydate1, float) or isinstance(pydate1, int):     # Absolute Time
            idate = _Date(absolute = pydate1)
        elif isinstance(pydate1, basestring):
            idate = _Date(datestr = pydate2.strip('"'))
        else:
            evaluation.message('DateDifference', 'date', date1)
            return

        if isinstance(pydate2, list):        # Date List
            fdate = _Date(datelist = pydate2)
        elif isinstance(pydate2, float) or isinstance(pydate2, int):     # Absolute Time
            fdate = _Date(absolute = pydate2)
        elif isinstance(pydate1, basestring):
            fdate = _Date(datestr = pydate2.strip('"'))
        else:
            evaluation.message('DateDifference', 'date', date2)
            return

        try:
            tdelta = fdate.date - idate.date
        except OverflowError:
            evaluation.message('General', 'ovf')
            return

        # Process Units
        pyunits = units.to_python()
        if isinstance(pyunits, unicode) or isinstance(pyunits, str):
            pyunits = [unicode(pyunits.strip('"'))]
        elif isinstance(pyunits, list) and all(isinstance(p, unicode)):
            pyunits = map(lambda p: p.strip('"'), pyunits)

        if not all(p in TIME_INCREMENTS.keys() for p in pyunits):
            evaluation.message('DateDifference', 'inc', units)

        def intdiv(a, b):
            'exact integer division where possible'
            if a % b == 0:
                return a / b
            else:
                return a / float(b)

        if len(pyunits) == 1:
            unit = pyunits[0]
            if tdelta.microseconds == 0:
                seconds = int(tdelta.total_seconds())
            else:
                seconds = tdelta.total_seconds()
            if unit == 'Year':
                result = [intdiv(seconds, 365*24*60*60), "Year"]
            if unit == 'Quarter':
                result = [intdiv(seconds, 365*6*60*60), "Quarter"]
            if unit == 'Month':
                result = [intdiv(seconds, 365*2*60*60), "Month"]
            if unit == 'Week':
                result = [intdiv(seconds, 7*24*60*60), "Week"]
            if unit == 'Day':
                result = intdiv(seconds, 24*60*60)
            if unit == 'Hour':
                result = [intdiv(seconds, 60*60) , "Hour"]
            if unit == 'Minute':
                result = [intdiv(secods, 60) , "Minute"]
            if unit == 'Second':
                result = [seconds, "Second"]
            return from_python(result)
        else:
            #TODO: Multiple Units
            return


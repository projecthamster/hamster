# pyTweener
#
# Tweening functions for python
#
# Heavily based on caurina Tweener: http://code.google.com/p/tweener/
#
# Released under M.I.T License - see above url
# Python version by Ben Harling 2009
# All kinds of slashing and dashing by Toms Baugis 2010
import math
import collections
import datetime as dt
import time
import re

class Tweener(object):
    def __init__(self, default_duration = None, tween = None):
        """Tweener
        This class manages all active tweens, and provides a factory for
        creating and spawning tween motions."""
        self.current_tweens = collections.defaultdict(set)
        self.default_easing = tween or Easing.Cubic.ease_in_out
        self.default_duration = default_duration or 1.0

    def has_tweens(self):
        return len(self.current_tweens) > 0


    def add_tween(self, obj, duration = None, easing = None, on_complete = None, on_update = None, delay = None, **kwargs):
        """
            Add tween for the object to go from current values to set ones.
            Example: add_tween(sprite, x = 500, y = 200, duration = 0.4)
            This will move the sprite to coordinates (500, 200) in 0.4 seconds.
            For parameter "easing" you can use one of the pytweener.Easing
            functions, or specify your own.
            The tweener can handle numbers, dates and color strings in hex ("#ffffff")
        """
        duration = duration or self.default_duration
        easing = easing or self.default_easing
        delay = delay or 0

        tw = Tween(obj, duration, easing, on_complete, on_update, delay, **kwargs )

        if obj in self.current_tweens:
            for current_tween in self.current_tweens[obj]:
                prev_keys = set((tweenable.key for tweenable in current_tween.tweenables))
                dif = prev_keys & set(kwargs.keys())

                removable = [tweenable for tweenable in current_tween.tweenables if tweenable.key in dif]
                for tweenable in removable:
                    current_tween.tweenables.remove(tweenable)


        self.current_tweens[obj].add(tw)
        return tw


    def get_tweens(self, obj):
        """Get a list of all tweens acting on the specified object
        Useful for manipulating tweens on the fly"""
        return self.current_tweens.get(obj, None)

    def kill_tweens(self, obj = None):
        """Stop tweening an object, without completing the motion or firing the
        on_complete"""
        if obj:
            try:
                del self.current_tweens[obj]
            except:
                pass
        else:
            self.current_tweens = collections.defaultdict(set)

    def remove_tween(self, tween):
        """"remove given tween without completing the motion or firing the on_complete"""
        if tween.target in self.current_tweens and tween in self.current_tweens[tween.target]:
            self.current_tweens[tween.target].remove(tween)

    def finish(self):
        """jump the the last frame of all tweens"""
        for obj in self.current_tweens:
            for t in self.current_tweens[obj]:
                t._update(t.duration)
        self.current_tweens = {}

    def update(self, delta_seconds):
        """update tweeners. delta_seconds is time in seconds since last frame"""

        done_list = set()
        for obj in self.current_tweens:
            for tween in self.current_tweens[obj]:
                done = tween._update(delta_seconds)
                if done:
                    done_list.add(tween)

        # remove all the completed tweens
        for tween in done_list:
            if tween.on_complete:
                tween.on_complete(tween.target)

            self.current_tweens[tween.target].remove(tween)
            if not self.current_tweens[tween.target]:
                del self.current_tweens[tween.target]


class Tweenable(object):
    hex_color_normal = re.compile("#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})")
    hex_color_short = re.compile("#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])")

    def __init__(self, key, start_value, target_value):
        self.key = key
        self.change = None
        self.decode_func = lambda x: x
        self.encode_func = lambda x: x
        self.start_value = start_value
        self.target_value = target_value

        if isinstance(start_value, int) or isinstance(start_value, float):
            self.start_value = start_value
            self.change = target_value - start_value
        else:
            if isinstance(start_value, dt.datetime) or isinstance(start_value, dt.date):
                self.decode_func = lambda x: time.mktime(x.timetuple())
                if isinstance(start_value, dt.datetime):
                    self.encode_func = lambda x: dt.datetime.fromtimestamp(x)
                else:
                    self.encode_func = lambda x: dt.date.fromtimestamp(x)

                self.start_value = self.decode_func(start_value)
                self.change = self.decode_func(target_value) - self.start_value

            elif isinstance(start_value, basestring) \
             and (self.hex_color_normal.match(start_value) or self.hex_color_short.match(start_value)):
                # code below is mainly based on jquery-color plugin
                self.encode_func = lambda val: "#%02x%02x%02x" % (max(min(val[0], 255), 0),
                                                                  max(min(val[1], 255), 0),
                                                                  max(min(val[2], 255), 0))
                if self.hex_color_normal.match(start_value):
                    self.decode_func = lambda val: [int(match, 16)
                                                    for match in self.hex_color_normal.match(val).groups()]

                elif self.hex_color_short.match(start_value):
                    self.decode_func = lambda val: [int(match + match, 16)
                                                    for match in self.hex_color_short.match(val).groups()]

                if self.hex_color_normal.match(target_value):
                    target_value = [int(match, 16)
                                    for match in self.hex_color_normal.match(target_value).groups()]
                else:
                    target_value = [int(match + match, 16)
                                    for match in self.hex_color_short.match(target_value).groups()]

                self.start_value = self.decode_func(start_value)
                self.change = [target - start for start, target in zip(self.start_value, target_value)]


    def update(self, ease, delta, duration):
        # list means we are dealing with a color triplet
        if isinstance(self.start_value, list):
            return self.encode_func([ease(delta, self.start_value[i],
                                                 self.change[i], duration)
                                                             for i in range(3)])
        else:
            return self.encode_func(ease(delta, self.start_value, self.change, duration))



class Tween(object):
    __slots__ = ('tweenables', 'target', 'delta', 'duration', 'delay',
                 'ease', 'delta', 'on_complete',
                 'on_update', 'complete', 'paused')

    def __init__(self, obj, duration, easing, on_complete, on_update, delay, **kwargs):
        """Tween object use Tweener.add_tween( ... ) to create"""
        self.duration = duration
        self.delay = delay
        self.target = obj
        self.ease = easing

        # list of (property, start_value, delta)
        self.tweenables = set()
        for key, value in kwargs.items():
            self.tweenables.add(Tweenable(key, self.target.__dict__[key], value))

        self.delta = 0
        self.on_complete = on_complete
        self.on_update = on_update
        self.complete = False

        self.paused = self.delay > 0

    def pause(self, seconds = -1):
        """Pause this tween
            do tween.pause( 2 ) to pause for a specific time
            or tween.pause() which pauses indefinitely."""
        self.paused = True
        self.delay = seconds

    def resume(self):
        """Resume from pause"""
        if self.paused:
            self.paused=False

    def _update(self, ptime):
        """Update tween with the time since the last frame
           if there is an update callback, it is always called
           whether the tween is running or paused"""

        if self.complete: return

        if self.paused:
            if self.delay > 0:
                self.delay = max(0, self.delay - ptime)
                if self.delay == 0:
                    self.paused = False
                    self.delay = -1
                if self.on_update:
                    self.on_update()
            return

        self.delta = self.delta + ptime
        if self.delta > self.duration:
            self.delta = self.duration

        for tweenable in self.tweenables:
            self.target.__setattr__(tweenable.key,
                                    tweenable.update(self.ease, self.delta, self.duration))

        if self.delta == self.duration:
            self.complete = True

        if self.on_update:
            self.on_update(self.target)

        return self.complete


"""Robert Penner's easing classes ported over from actionscript by Toms Baugis (at gmail com).
There certainly is room for improvement, but wanted to keep the readability to some extent.

================================================================================
 Easing Equations
 (c) 2003 Robert Penner, all rights reserved.
 This work is subject to the terms in
 http://www.robertpenner.com/easing_terms_of_use.html.
================================================================================

TERMS OF USE - EASING EQUATIONS

Open source under the BSD License.

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.
    * Neither the name of the author nor the names of contributors may be used
      to endorse or promote products derived from this software without specific
      prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
class Easing(object):
    """Class containing easing classes to use together with the tweener.
       All of the classes have :func:`ease_in`, :func:`ease_out` and
       :func:`ease_in_out` functions."""

    class Back(object):
        @staticmethod
        def ease_in(t, b, c, d, s = 1.70158):
            t = t / d
            return c * t * t * ((s+1) * t - s) + b

        @staticmethod
        def ease_out (t, b, c, d, s = 1.70158):
            t = t / d - 1
            return c * (t * t * ((s + 1) * t + s) + 1) + b

        @staticmethod
        def ease_in_out (t, b, c, d, s = 1.70158):
            t = t / (d * 0.5)
            s = s * 1.525

            if t < 1:
                return c * 0.5 * (t * t * ((s + 1) * t - s)) + b

            t = t - 2
            return c / 2 * (t * t * ((s + 1) * t + s) + 2) + b

    class Bounce(object):
        @staticmethod
        def ease_out (t, b, c, d):
            t = t / d
            if t < 1 / 2.75:
                return c * (7.5625 * t * t) + b
            elif t < 2 / 2.75:
                t = t - 1.5 / 2.75
                return c * (7.5625 * t * t + 0.75) + b
            elif t < 2.5 / 2.75:
                t = t - 2.25 / 2.75
                return c * (7.5625 * t * t + .9375) + b
            else:
                t = t - 2.625 / 2.75
                return c * (7.5625 * t * t + 0.984375) + b

        @staticmethod
        def ease_in (t, b, c, d):
            return c - Easing.Bounce.ease_out(d-t, 0, c, d) + b

        @staticmethod
        def ease_in_out (t, b, c, d):
            if t < d * 0.5:
                return Easing.Bounce.ease_in (t * 2, 0, c, d) * .5 + b

            return Easing.Bounce.ease_out (t * 2 -d, 0, c, d) * .5 + c*.5 + b



    class Circ(object):
        @staticmethod
        def ease_in (t, b, c, d):
            t = t / d
            return -c * (math.sqrt(1 - t * t) - 1) + b

        @staticmethod
        def ease_out (t, b, c, d):
            t = t / d - 1
            return c * math.sqrt(1 - t * t) + b

        @staticmethod
        def ease_in_out (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return -c * 0.5 * (math.sqrt(1 - t * t) - 1) + b

            t = t - 2
            return c*0.5 * (math.sqrt(1 - t * t) + 1) + b


    class Cubic(object):
        @staticmethod
        def ease_in (t, b, c, d):
            t = t / d
            return c * t * t * t + b

        @staticmethod
        def ease_out (t, b, c, d):
            t = t / d - 1
            return c * (t * t * t + 1) + b

        @staticmethod
        def ease_in_out (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t * t * t + b

            t = t - 2
            return c * 0.5 * (t * t * t + 2) + b


    class Elastic(object):
        @staticmethod
        def ease_in (t, b, c, d, a = 0, p = 0):
            if t==0: return b

            t = t / d
            if t == 1: return b+c

            if not p: p = d * .3;

            if not a or a < abs(c):
                a = c
                s = p / 4
            else:
                s = p / (2 * math.pi) * math.asin(c / a)

            t = t - 1
            return - (a * math.pow(2, 10 * t) * math.sin((t*d-s) * (2 * math.pi) / p)) + b


        @staticmethod
        def ease_out (t, b, c, d, a = 0, p = 0):
            if t == 0: return b

            t = t / d
            if (t == 1): return b + c

            if not p: p = d * .3;

            if not a or a < abs(c):
                a = c
                s = p / 4
            else:
                s = p / (2 * math.pi) * math.asin(c / a)

            return a * math.pow(2,-10 * t) * math.sin((t * d - s) * (2 * math.pi) / p) + c + b


        @staticmethod
        def ease_in_out (t, b, c, d, a = 0, p = 0):
            if t == 0: return b

            t = t / (d * 0.5)
            if t == 2: return b + c

            if not p: p = d * (.3 * 1.5)

            if not a or a < abs(c):
                a = c
                s = p / 4
            else:
                s = p / (2 * math.pi) * math.asin(c / a)

            if (t < 1):
                t = t - 1
                return -.5 * (a * math.pow(2, 10 * t) * math.sin((t * d - s) * (2 * math.pi) / p)) + b

            t = t - 1
            return a * math.pow(2, -10 * t) * math.sin((t * d - s) * (2 * math.pi) / p) * .5 + c + b


    class Expo(object):
        @staticmethod
        def ease_in(t, b, c, d):
            if t == 0:
                return b
            else:
                return c * math.pow(2, 10 * (t / d - 1)) + b - c * 0.001

        @staticmethod
        def ease_out(t, b, c, d):
            if t == d:
                return b + c
            else:
                return c * (-math.pow(2, -10 * t / d) + 1) + b

        @staticmethod
        def ease_in_out(t, b, c, d):
            if t==0:
                return b
            elif t==d:
                return b+c

            t = t / (d * 0.5)

            if t < 1:
                return c * 0.5 * math.pow(2, 10 * (t - 1)) + b

            return c * 0.5 * (-math.pow(2, -10 * (t - 1)) + 2) + b


    class Linear(object):
        @staticmethod
        def ease_none(t, b, c, d):
            return c * t / d + b

        @staticmethod
        def ease_in(t, b, c, d):
            return c * t / d + b

        @staticmethod
        def ease_out(t, b, c, d):
            return c * t / d + b

        @staticmethod
        def ease_in_out(t, b, c, d):
            return c * t / d + b


    class Quad(object):
        @staticmethod
        def ease_in (t, b, c, d):
            t = t / d
            return c * t * t + b

        @staticmethod
        def ease_out (t, b, c, d):
            t = t / d
            return -c * t * (t-2) + b

        @staticmethod
        def ease_in_out (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t * t + b

            t = t - 1
            return -c * 0.5 * (t * (t - 2) - 1) + b


    class Quart(object):
        @staticmethod
        def ease_in (t, b, c, d):
            t = t / d
            return c * t * t * t * t + b

        @staticmethod
        def ease_out (t, b, c, d):
            t = t / d - 1
            return -c * (t * t * t * t - 1) + b

        @staticmethod
        def ease_in_out (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t * t * t * t + b

            t = t - 2
            return -c * 0.5 * (t * t * t * t - 2) + b


    class Quint(object):
        @staticmethod
        def ease_in (t, b, c, d):
            t = t / d
            return c * t * t * t * t * t + b

        @staticmethod
        def ease_out (t, b, c, d):
            t = t / d - 1
            return c * (t * t * t * t * t + 1) + b

        @staticmethod
        def ease_in_out (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t * t * t * t * t + b

            t = t - 2
            return c * 0.5 * (t * t * t * t * t + 2) + b

    class Sine(object):
        @staticmethod
        def ease_in (t, b, c, d):
            return -c * math.cos(t / d * (math.pi / 2)) + c + b

        @staticmethod
        def ease_out (t, b, c, d):
            return c * math.sin(t / d * (math.pi / 2)) + b

        @staticmethod
        def ease_in_out (t, b, c, d):
            return -c * 0.5 * (math.cos(math.pi * t / d) - 1) + b


    class Strong(object):
        @staticmethod
        def ease_in(t, b, c, d):
            return c * (t/d)**5 + b

        @staticmethod
        def ease_out(t, b, c, d):
            return c * ((t / d - 1)**5 + 1) + b

        @staticmethod
        def ease_in_out(t, b, c, d):
            t = t / (d * 0.5)

            if t < 1:
                return c * 0.5 * t * t * t * t * t + b

            t = t - 2
            return c * 0.5 * (t * t * t * t * t + 2) + b




class _PerformanceTester(object):
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

if __name__ == "__main__":
    import datetime as dt

    tweener = Tweener()
    objects = []
    for i in range(10000):
        objects.append(_PerformanceTester(dt.datetime.now(), i-100, i-100))


    total = dt.datetime.now()

    t = dt.datetime.now()
    for i, o in enumerate(objects):
        tweener.add_tween(o, a = dt.datetime.now() - dt.timedelta(days=3), b = i, c = i, duration = 1.0)
    print "add", dt.datetime.now() - t

    tweener.finish()
    print objects[0].a

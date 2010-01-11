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

class Tweener(object):
    def __init__(self, default_duration = None, tween = None):
        """Tweener
        This class manages all active tweens, and provides a factory for
        creating and spawning tween motions."""
        self.currentTweens = {}
        self.defaultTweenType = tween or Easing.Cubic.easeInOut
        self.defaultDuration = default_duration or 1.0

    def hasTweens(self):
        return len(self.currentTweens) > 0


    def addTween(self, obj, **kwargs):
        """ addTween( object, **kwargs) -> tweenObject or False

            Example:
            tweener.addTween( myRocket, throttle=50, setThrust=400, tweenTime=5.0, tweenType=tweener.OUT_QUAD )

            You must first specify an object, and at least one property or function with a corresponding
            change value. The tween will throw an error if you specify an attribute the object does
            not possess. Also the data types of the change and the initial value of the tweened item
            must match. If you specify a 'set' -type function, the tweener will attempt to get the
            starting value by call the corresponding 'get' function on the object. If you specify a
            property, the tweener will read the current state as the starting value. You add both
            functions and property changes to the same tween.

            in addition to any properties you specify on the object, these keywords do additional
            setup of the tween.

            tweenTime = the duration of the motion
            tweenType = one of the predefined tweening equations or your own function
            onComplete = specify a function to call on completion of the tween
            onUpdate = specify a function to call every time the tween updates
            tweenDelay = specify a delay before starting.
            """
        if "tweenTime" in kwargs:
            t_time = kwargs.pop("tweenTime")
        else: t_time = self.defaultDuration

        if "tweenType" in kwargs:
            t_type = kwargs.pop("tweenType")
        else: t_type = self.defaultTweenType

        if "onComplete" in kwargs:
            t_completeFunc = kwargs.pop("onComplete")
        else: t_completeFunc = None

        if "onUpdate" in kwargs:
            t_updateFunc = kwargs.pop("onUpdate")
        else: t_updateFunc = None

        if "tweenDelay" in kwargs:
            t_delay = kwargs.pop("tweenDelay")
        else: t_delay = 0

        tw = Tween( obj, t_time, t_type, t_completeFunc, t_updateFunc, t_delay, **kwargs )
        if tw:
            tweenlist = self.currentTweens.setdefault(obj, [])
            tweenlist.append(tw)
        return tw

    def removeTween(self, tweenObj):
        tweenObj.complete = True

    def getTweensAffectingObject(self, obj):
        """Get a list of all tweens acting on the specified object
        Useful for manipulating tweens on the fly"""
        return self.currentTweens.get(obj, [])

    def killTweensOf(self, obj):
        """Stop tweening an object, without completing the motion
        or firing the completeFunction"""
        try:
            del self.currentTweens[obj]
        except:
            pass


    def finish(self):
        #go to last frame for all tweens
        for obj in self.currentTweens:
            for t in self.currentTweens[obj]:
                t.update(t.duration)
        self.currentTweens = {}

    def update(self, timeSinceLastFrame):
        for obj in self.currentTweens.keys():
            # updating tweens from last to first and deleting while at it
            # in order to not confuse the index
            for i, t in reversed(list(enumerate(self.currentTweens[obj]))):
                t.update(timeSinceLastFrame)
                if t.complete:
                    del self.currentTweens[obj][i]

                if not self.currentTweens[obj]:
                    del self.currentTweens[obj]

class Tween(object):
    __slots__ = ['duration', 'delay', 'target', 'tween', 'tweenables', 'delta',
                 'target', 'ease', 'tweenables', 'delta', 'completeFunction',
                 'updateFunction', 'complete', 'paused']

    def __init__(self, obj, duration, easing, on_complete, on_update, delay, **kwargs):
        """Tween object use Tweener.addTween( ... ) to create"""
        self.duration = duration
        self.delay = delay
        self.target = obj
        self.ease = easing

        # list of (property, start_value, end_value)
        self.tweenables = [(k, self.target.__dict__[k], v) for k, v in kwargs.items()]

        self.delta = 0
        self.completeFunction = on_complete
        self.updateFunction = on_update
        self.complete = False

        self.paused = self.delay > 0

    def pause( self, numSeconds=-1 ):
        """Pause this tween
            do tween.pause( 2 ) to pause for a specific time
            or tween.pause() which pauses indefinitely."""
        self.paused = True
        self.delay = numSeconds

    def resume( self ):
        """Resume from pause"""
        if self.paused:
            self.paused=False

    def update(self, ptime):
        """Update tween with the time since the last frame
           if there is an update callback, it is always called
           whether the tween is running or paused"""

        if self.complete:
            return

        if self.paused:
            if self.delay > 0:
                self.delay = max( 0, self.delay - ptime )
                if self.delay == 0:
                    self.paused = False
                    self.delay = -1
                if self.updateFunction:
                    self.updateFunction()
            return

        self.delta = self.delta + ptime
        if self.delta > self.duration:
            self.delta = self.duration


        for prop, start_value, end_value in self.tweenables:
            self.target.__dict__[prop] = self.ease(self.delta, start_value, end_value - start_value, self.duration)

        if self.delta == self.duration:
            self.complete = True
            if self.completeFunction:
                self.completeFunction()

        if self.updateFunction:
            self.updateFunction()


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
    class Back(object):
        @staticmethod
        def easeIn(t, b, c, d, s = 1.70158):
            t = t / d
            return c * t * t * ((s+1) * t - s) + b

        @staticmethod
        def easeOut (t, b, c, d, s = 1.70158):
            t = t / d - 1
            return c * (t * t * ((s + 1) * t + s) + 1) + b

        @staticmethod
        def easeInOut (t, b, c, d, s = 1.70158):
            t = t / (d * 0.5)
            s = s * 1.525

            if t < 1:
                return c * 0.5 * (t * t * ((s + 1) * t - s)) + b

            t = t - 2
            return c / 2 * (t * t * ((s + 1) * t + s) + 2) + b

    class Bounce(object):
        @staticmethod
        def easeOut (t, b, c, d):
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
        def easeIn (t, b, c, d):
            return c - Easing.Bounce.easeOut(d-t, 0, c, d) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            if t < d * 0.5:
                return Easing.Bounce.easeIn (t * 2, 0, c, d) * .5 + b

            return Easing.Bounce.easeOut (t * 2 -d, 0, c, d) * .5 + c*.5 + b



    class Circ(object):
        @staticmethod
        def easeIn (t, b, c, d):
            t = t / d
            return -c * (math.sqrt(1 - t * t) - 1) + b

        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d - 1
            return c * math.sqrt(1 - t * t) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return -c * 0.5 * (math.sqrt(1 - t * t) - 1) + b

            t = t - 2
            return c*0.5 * (math.sqrt(1 - t * t) + 1) + b


    class Cubic(object):
        @staticmethod
        def easeIn (t, b, c, d):
            t = t / d
            return c * t * t * t + b

        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d - 1
            return c * (t * t * t + 1) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t * t * t + b

            t = t - 2
            return c * 0.5 * (t * t * t + 2) + b


    class Elastic(object):
        @staticmethod
        def easeIn (t, b, c, d, a = 0, p = 0):
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
        def easeOut (t, b, c, d, a = 0, p = 0):
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
        def easeInOut (t, b, c, d, a = 0, p = 0):
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
        def easeIn(t, b, c, d):
            if t == 0:
                return b
            else:
                return c * math.pow(2, 10 * (t / d - 1)) + b - c * 0.001

        @staticmethod
        def easeOut(t, b, c, d):
            if t == d:
                return b + c
            else:
                return c * (-math.pow(2, -10 * t / d) + 1) + b

        @staticmethod
        def easeInOut(t, b, c, d):
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
        def easeNone(t, b, c, d):
            return c * t / d + b

        @staticmethod
        def easeIn(t, b, c, d):
            return c * t / d + b

        @staticmethod
        def easeOut(t, b, c, d):
            return c * t / d + b

        @staticmethod
        def easeInOut(t, b, c, d):
            return c * t / d + b


    class Quad(object):
        @staticmethod
        def easeIn (t, b, c, d):
            t = t / d
            return c * t * t + b

        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d
            return -c * t * (t-2) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t * t + b

            t = t - 1
            return -c * 0.5 * (t * (t - 2) - 1) + b


    class Quart(object):
        @staticmethod
        def easeIn (t, b, c, d):
            t = t / d
            return c * t * t * t * t + b

        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d - 1
            return -c * (t * t * t * t - 1) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t * t * t * t + b

            t = t - 2
            return -c * 0.5 * (t * t * t * t - 2) + b


    class Quint(object):
        @staticmethod
        def easeIn (t, b, c, d):
            t = t / d
            return c * t * t * t * t * t + b

        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d - 1
            return c * (t * t * t * t * t + 1) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t * t * t * t * t + b

            t = t - 2
            return c * 0.5 * (t * t * t * t * t + 2) + b

    class Sine(object):
        @staticmethod
        def easeIn (t, b, c, d):
            return -c * math.cos(t / d * (math.pi / 2)) + c + b

        @staticmethod
        def easeOut (t, b, c, d):
            return c * math.sin(t / d * (math.pi / 2)) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            return -c * 0.5 * (math.cos(math.pi * t / d) - 1) + b


    class Strong(object):
        @staticmethod
        def easeIn(t, b, c, d):
            return c * (t/d)**5 + b

        @staticmethod
        def easeOut(t, b, c, d):
            return c * ((t / d - 1)**5 + 1) + b

        @staticmethod
        def easeInOut(t, b, c, d):
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
        objects.append(_PerformanceTester(i-100, i-100, i-100))


    total = dt.datetime.now()

    t = dt.datetime.now()
    for i, o in enumerate(objects):
        tweener.addTween(o, a = i, b = i, c = i, tweenTime = 1.0)
    print "add", dt.datetime.now() - t

    t = dt.datetime.now()

    for i in range(10):
        tweener.update(0.01)
    print "update", dt.datetime.now() - t

    t = dt.datetime.now()

    for i in range(10):
        for i, o in enumerate(objects):
            tweener.killTweensOf(o)
            tweener.addTween(o, a = i, b = i, c = i, tweenTime = 1.0)
    print "kill-add", dt.datetime.now() - t

    print "total", dt.datetime.now() - total



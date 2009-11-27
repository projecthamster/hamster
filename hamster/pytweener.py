# pyTweener
#
# Tweening functions for python
#
# Heavily based on caurina Tweener: http://code.google.com/p/tweener/
#
# Released under M.I.T License - see above url
# Python version by Ben Harling 2009 
import math

class Tweener:
    def __init__(self, duration = 0.5, tween = None):
        """Tweener
        This class manages all active tweens, and provides a factory for
        creating and spawning tween motions."""
        self.currentTweens = []
        self.defaultTweenType = tween or Easing.Cubic.easeInOut
        self.defaultDuration = duration or 1.0
 
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
            onCompleteFunction = specify a function to call on completion of the tween
            onUpdateFunction = specify a function to call every time the tween updates
            tweenDelay = specify a delay before starting.
            """
        if "tweenTime" in kwargs:
            t_time = kwargs.pop("tweenTime")
        else: t_time = self.defaultDuration
 
        if "tweenType" in kwargs:
            t_type = kwargs.pop("tweenType")
        else: t_type = self.defaultTweenType
 
        if "onCompleteFunction" in kwargs:
            t_completeFunc = kwargs.pop("onCompleteFunction")
        else: t_completeFunc = None
 
        if "onUpdateFunction" in kwargs:
            t_updateFunc = kwargs.pop("onUpdateFunction")
        else: t_updateFunc = None
 
        if "tweenDelay" in kwargs:
            t_delay = kwargs.pop("tweenDelay")
        else: t_delay = 0
 
        tw = Tween( obj, t_time, t_type, t_completeFunc, t_updateFunc, t_delay, **kwargs )
        if tw:    
            self.currentTweens.append( tw )
        return tw
 
    def removeTween(self, tweenObj):
        if tweenObj in self.currentTweens:
            tweenObj.complete = True
            #self.currentTweens.remove( tweenObj )
 
    def getTweensAffectingObject(self, obj):
        """Get a list of all tweens acting on the specified object
        Useful for manipulating tweens on the fly"""
        tweens = []
        for t in self.currentTweens:
            if t.target is obj:
                tweens.append(t)
        return tweens
 
    def removeTweeningFrom(self, obj):
        """Stop tweening an object, without completing the motion
        or firing the completeFunction"""
        for t in self.currentTweens:
            if t.target is obj:
                t.complete = True
 
    def finish(self):
        #go to last frame for all tweens
        for t in self.currentTweens:
            t.update(t.duration)
        self.currentTweens = []
 
    def update(self, timeSinceLastFrame):
        removable = []
        for t in self.currentTweens:
            t.update(timeSinceLastFrame)

            if t.complete:
                removable.append(t)
                
        for t in removable:
            self.currentTweens.remove(t)
            
 
class Tween(object):
    def __init__(self, obj, tduration, tweenType, completeFunction, updateFunction, delay, **kwargs):
        """Tween object:
            Can be created directly, but much more easily using Tweener.addTween( ... )
            """
        #print obj, tduration, kwargs
        self.duration = tduration
        self.delay = delay
        self.target = obj
        self.tween = tweenType
        self.tweenables = kwargs
        self.delta = 0
        self.completeFunction = completeFunction
        self.updateFunction = updateFunction
        self.complete = False
        self.tProps = []
        self.tFuncs = []
        self.paused = self.delay > 0
        self.decodeArguments()
 
    def decodeArguments(self):
        """Internal setup procedure to create tweenables and work out
           how to deal with each"""
 
        if len(self.tweenables) == 0:
            # nothing to do 
            print "TWEEN ERROR: No Tweenable properties or functions defined"
            self.complete = True
            return
 
        for k, v in self.tweenables.items():
 
        # check that its compatible
            if not hasattr( self.target, k):
                print "TWEEN ERROR: " + str(self.target) + " has no function " + k
                self.complete = True
                break
 
            prop = func = False
            startVal = 0
            newVal = v
 
            try:
                startVal = self.target.__dict__[k]
                prop = k
                propName = k
 
            except:
                func = getattr( self.target, k)
                funcName = k
 
            if func:
                try:
                    getFunc = getattr(self.target, funcName.replace("set", "get") )
                    startVal = getFunc()
                except:
                    # no start value, assume its 0
                    # but make sure the start and change
                    # dataTypes match :)
                    startVal = newVal * 0
                tweenable = Tweenable( startVal, newVal - startVal)    
                newFunc = [ k, func, tweenable]
 
                #setattr(self, funcName, newFunc[2])
                self.tFuncs.append( newFunc )
 
 
            if prop:
                tweenable = Tweenable( startVal, newVal - startVal)    
                newProp = [ k, prop, tweenable]
                self.tProps.append( newProp )  
 
 
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
        """Update this tween with the time since the last frame
            if there is an update function, it is always called
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
 
        self.delta = min(self.delta + ptime, self.duration)
 

        for propName, prop, tweenable in self.tProps:
            self.target.__dict__[prop] = self.tween( self.delta, tweenable.startValue, tweenable.change, self.duration )
        for funcName, func, tweenable in self.tFuncs:
            func( self.tween( self.delta, tweenable.startValue, tweenable.change, self.duration ) )
 
 
        if self.delta == self.duration:
            self.complete = True
            if self.completeFunction:
                self.completeFunction()
 
        if self.updateFunction:
            self.updateFunction()
 
 
 
    def getTweenable(self, name):
        """Return the tweenable values corresponding to the name of the original
        tweening function or property. 
 
        Allows the parameters of tweens to be changed at runtime. The parameters
        can even be tweened themselves!
 
        eg:
 
        # the rocket needs to escape!! - we're already moving, but must go faster!
        twn = tweener.getTweensAffectingObject( myRocket )[0]
        tweenable = twn.getTweenable( "thrusterPower" )
        tweener.addTween( tweenable, change=1000.0, tweenTime=0.4, tweenType=tweener.IN_QUAD )
 
        """
        ret = None
        for n, f, t in self.tFuncs:
            if n == name:
                ret = t
                return ret
        for n, p, t in self.tProps:
            if n == name:
                ret = t
                return ret
        return ret
 
    def Remove(self):
        """Disables and removes this tween
            without calling the complete function"""
        self.complete = True

 
class Tweenable:
    def __init__(self, start, change):
        """Tweenable:
            Holds values for anything that can be tweened
            these are normally only created by Tweens"""
        self.startValue = start
        self.change = change


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
class Easing:
    class Back:
        @staticmethod
        def easeIn(t, b, c, d, s = 1.70158):
            t = t / d
            return c * t**2 * ((s+1) * t - s) + b

        @staticmethod
        def easeOut (t, b, c, d, s = 1.70158):
            t = t / d - 1
            return c * (t**2 * ((s + 1) * t + s) + 1) + b

        @staticmethod
        def easeInOut (t, b, c, d, s = 1.70158):
            t = t / (d * 0.5)
            s = s * 1.525
            
            if t < 1:
                return c * 0.5 * (t**2 * ((s + 1) * t - s)) + b

            t = t - 2
            return c / 2 * (t**2 * ((s + 1) * t + s) + 2) + b

    class Bounce:
        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d
            if t < 1 / 2.75:
                return c * (7.5625 * t**2) + b
            elif t < 2 / 2.75:
                t = t - 1.5 / 2.75
                return c * (7.5625 * t**2 + 0.75) + b
            elif t < 2.5 / 2.75:
                t = t - 2.25 / 2.75
                return c * (7.5625 * t**2 + .9375) + b
            else:
                t = t - 2.625 / 2.75
                return c * (7.5625 * t**2 + 0.984375) + b

        @staticmethod
        def easeIn (t, b, c, d):
            return c - Easing.Bounce.easeOut(d-t, 0, c, d) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            if t < d * 0.5:
                return Easing.Bounce.easeIn (t * 2, 0, c, d) * .5 + b

            return Easing.Bounce.easeOut (t * 2 -d, 0, c, d) * .5 + c*.5 + b


        
    class Circ:
        @staticmethod
        def easeIn (t, b, c, d):
            t = t / d
            return -c * (math.sqrt(1 - t**2) - 1) + b

        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d - 1
            return c * math.sqrt(1 - t**2) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return -c * 0.5 * (math.sqrt(1 - t**2) - 1) + b
            
            t = t - 2
            return c*0.5 * (math.sqrt(1 - t**2) + 1) + b


    class Cubic:
        @staticmethod
        def easeIn (t, b, c, d):
            t = t / d
            return c * t**3 + b

        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d - 1
            return c * (t**3 + 1) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t**3 + b
            
            t = t - 2
            return c * 0.5 * (t**3 + 2) + b


    class Elastic:
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


    class Expo:
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


    class Linear:
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


    class Quad:
        @staticmethod
        def easeIn (t, b, c, d):
            t = t / d
            return c * t**2 + b

        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d
            return -c * t * (t-2) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t**2 + b
            
            t = t - 1
            return -c * 0.5 * (t * (t - 2) - 1) + b


    class Quart:
        @staticmethod
        def easeIn (t, b, c, d):
            t = t / d
            return c * t**4 + b

        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d - 1
            return -c * (t**4 - 1) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t**4 + b
            
            t = t - 2
            return -c * 0.5 * (t**4 - 2) + b

    
    class Quint:
        @staticmethod
        def easeIn (t, b, c, d):
            t = t / d
            return c * t**5 + b

        @staticmethod
        def easeOut (t, b, c, d):
            t = t / d - 1
            return c * (t**5 + 1) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            t = t / (d * 0.5)
            if t < 1:
                return c * 0.5 * t**5 + b
            
            t = t - 2
            return c * 0.5 * (t**5 + 2) + b

    class Sine:
        @staticmethod
        def easeIn (t, b, c, d):
            return -c * math.cos(t / d * (math.pi / 2)) + c + b

        @staticmethod
        def easeOut (t, b, c, d):
            return c * math.sin(t / d * (math.pi / 2)) + b

        @staticmethod
        def easeInOut (t, b, c, d):
            return -c * 0.5 * (math.cos(math.pi * t / d) - 1) + b


    class Strong:
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
                return c * 0.5 * t**5 + b
            
            t = t - 2
            return c * 0.5 * (t**5 + 2) + b



class TweenTestObject:
    def __init__(self):
        self.pos = 20
        self.rot = 50
 
    def update(self):
        print self.pos, self.rot
 
    def setRotation(self, rot):
        self.rot = rot
 
    def getRotation(self):
        return self.rot
 
    def complete(self):
        print "I'm done tweening now mommy!"
 
 
if __name__=="__main__":
    import time
    T = Tweener()
    tst = TweenTestObject()
    mt = T.addTween( tst, setRotation=500.0, tweenTime=2.5, tweenType=T.OUT_EXPO, 
                      pos=-200, tweenDelay=0.4, onCompleteFunction=tst.complete, 
                      onUpdateFunction=tst.update )
    s = time.clock()
    changed = False
    while T.hasTweens():
        tm = time.clock()
        d = tm - s
        s = tm
        T.update( d )
        if mt.delta > 1.0 and not changed:
 
            tweenable = mt.getTweenable( "setRotation" )
 
            T.addTween( tweenable, change=-1000, tweenTime=0.7 )
            T.addTween( mt, duration=-0.2, tweenTime=0.2 )
            changed = True
        #print mt.duration,
        print tst.getRotation(), tst.pos
        time.sleep(0.06)
    print tst.getRotation(), tst.pos

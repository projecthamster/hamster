"""Small charting library that enables you to draw simple bar and
horizontal bar charts. This library is not intended for scientific graphs.
More like some visual clues to the user.

Currently chart understands only list of four member lists, in label, value
fashion. Like:
    data = [
        ["Label1", value1, color(optional), background(optional)],
        ["Label2", value2 color(optional), background(optional)],
        ["Label3", value3 color(optional), background(optional)],
    ]

Author: toms.baugis@gmail.com
Licensed under LGPL - do whatever you want, and send me some cookies, if you
feel like it.
Feel free to contribute - more info at Project Hamster web page:
http://projecthamster.wordpress.com/

Example:
    # create new chart object
    chart = Chart(max_bar_width = 40, collapse_whitespace = True) 
    
    eventBox = gtk.EventBox() # charts go into eventboxes, or windows
    place = self.get_widget("totals_by_day") #just some placeholder

    eventBox.add(chart);
    place.add(eventBox)

    #Let's imagine that we count how many apples we have gathered, by day
    data = [["Mon", 20], ["Tue", 12], ["Wed", 80],
            ["Thu", 60], ["Fri", 40], ["Sat", 0], ["Sun", 0]]
    self.day_chart.plot(data)

"""

import gtk
import gobject
import cairo
import copy
import math

# Tango colors
light = [(252, 233, 79),  (138, 226, 52),  (252, 175, 62),
         (114, 159, 207), (173, 127, 168), (233, 185, 110),
         (239, 41,  41),  (238, 238, 236), (136, 138, 133)]

medium = [(237, 212, 0),   (115, 210, 22),  (245, 121, 0),
          (52,  101, 164), (117, 80,  123), (193, 125, 17),
          (204, 0,   0),   (211, 215, 207), (85, 87, 83)]

dark = [(196, 160, 0), (78, 154, 6), (206, 92, 0),
        (32, 74, 135), (92, 53, 102), (143, 89, 2),
        (164, 0, 0), (186, 189, 182), (46, 52, 54)]

color_count = len(light)

def set_color(context, color):
    r,g,b = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
    context.set_source_rgb(r, g, b)
    
    
class Chart(gtk.DrawingArea):
    """Chart constructor. Optional arguments:
        cycle_colors = [True|False] - should every bar get it's own color.
                                      Defaults to False
        orient_vertical = [True|False] - Chart orientation.
                                         Defaults to vertical
        max_bar_width = pixels - Maximal width of bar. If not specified,
                                 bars will stretch to fill whole area
        values_on_bars = [True|False] - Should bar values displayed on each bar.
                                        Defaults to False
        collapse_whitespace = [True|False] - If max_bar_width is set, should
                                             we still fill the graph area with
                                             the white stuff and grids and such.
                                             Defaults to false
        stretch_grid = [True|False] - Should the grid be of fixed or flex
                                      size. If set to true, graph will be split
                                      in 4 parts, which will stretch on resize.
                                      Defaults to False.
        animate = [True|False] - Should the bars grow/shrink on redrawing.
                                 Animation happens only if labels and their
                                 order match.
                                 Defaults to True.

        Then there are some defaults, you can override:
        default_grid_stride - If stretch_grid is set to false, this allows you
                              to choose granularity of grid. Defaults to 50
        animation_frames - in how many steps should the animation be done
        animation_timeout - after how many miliseconds should we draw next frame
    """
    def __init__(self, **args):
        """here is init"""
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self._expose)
        self.data, self.prev_data = None, None #start off with an empty hand
        
        """now see what we have in args!"""
        self.cycle_colors = "cycle_colors" in args and args["cycle_colors"] # defaults to false
        self.orient_vertical = "orient" not in args or args["orient"] == "vertical" # defaults to true
        
        self.max_bar_width = None
        if "max_bar_width" in args: self.max_bar_width = args["max_bar_width"]        

        self.values_on_bars = "values_on_bars" in args and args["values_on_bars"] #defaults to false

        self.collapse_whitespace = "collapse_whitespace" in args and args["collapse_whitespace"] #defaults to false
        
        self.stretch_grid = "stretch_grid" in args and args["stretch_grid"] #defaults to false

        self.animate = "animate" not in args or args["animate"] # defaults to true
        
        #and some defaults
        self.default_grid_stride = 50
        
        self.animation_frames = 150
        self.animation_timeout = 20 #in miliseconds

        self.current_frame = self.animation_frames
        self.freeze_animation = False
        
    def _expose(self, widget, event): # expose is when drawing's going on
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        context.clip()
        
        if self.orient_vertical:
            # for simple bars figure, when there is way too much data for bars
            # and go to lines (yay!)
            if len(self.data) == 0 or (event.area.width / len(self.data)) > 30: #this is big enough
                self._bar_chart(context)
            else:
                self._area_chart(context)
            
            
        else:
            self._horizontal_bar_chart(context)

        return False

    def plot(self, data):
        """Draw chart with given data
            Currently chart understands only list of two member lists, in label, value
            fashion. Like:
                data = [
                    ["Label1", value1],
                    ["Label2", value2],
                    ["Label3", value3],
                ]
        """
        
        #check if maybe this chart is animation enabled and we are in middle of animation
        if self.animate and self.current_frame < self.animation_frames: #something's going on here!
            self.freeze_animation = True #so we don't catch some nasty race condition
            
            self.prev_data = copy.copy(self.data)
            self.new_data, self.max = self._get_factors(data)
            
            #if so, let's start where we are and move to the new set inst
            self.current_frame = 0 #start the animation from beginning
            self.freeze_animation = False
            return
        
        
                

        if self.animate:
            """chart animation means gradually moving from previous data set
               to the new one. prev_data will be the previous set, new_data
               is copy of the data we have been asked to plot, and data itself
               will be the moving thing"""
               
            self.current_frame = 0
            self.new_data, self.max = self._get_factors(data)

            if not self.prev_data: #if there is no previous data, set it to zero, so we get a growing animation
                self.prev_data = copy.deepcopy(self.new_data)
                for i in range(len(self.prev_data)):
                    self.prev_data[i]["factor"] = 0
                    
            self.data = copy.copy(self.prev_data)


            gobject.timeout_add(self.animation_timeout, self._replot)
        else:
            self.data, self.max = self._get_factors(data)
            self._invalidate()

    
    def _replot(self):
        """Internal function to do the math, going from previous set to the
           new one, and redraw graph"""
        if self.freeze_animation:
            return True #just wait until they release us!

        if self.window:    #this can get called before expose    
            # do some sanity checks before thinking about animation
            # are the source and target of same length?
            if len(self.prev_data) != len(self.new_data):
                self.prev_data = copy.copy(self.new_data)
                self.data = copy.copy(self.new_data)
                self.current_frame = self.animation_frames #stop animation
                self._invalidate()
                return False
            
            # have they same labels? (that's important!)
            for i in range(len(self.prev_data)):
                if self.prev_data[i]["label"] != self.new_data[i]["label"]:
                    self.prev_data = copy.copy(self.new_data)
                    self.data = copy.copy(self.new_data)
                    self.current_frame = self.animation_frames #stop animation
                    self._invalidate()
                    return False
            

            #ok, now we are good!
            self.current_frame = self.current_frame + 1
            

            # using sines for some "swoosh" animation (not really noticeable)
            # sin(0) = 0; sin(pi/2) = 1
            pi_factor = math.sin((math.pi / 2.0) * (self.current_frame / float(self.animation_frames)))
            #pi_factor = math.sqrt(pi_factor) #stretch it a little so the animation can be seen a little better
            
            # here we do the magic - go from prev to new
            # we are fiddling with the calculated sizes instead of raw data - that's much safer
            bars_below_lim = 0
            
            for i in range(len(self.data)):
                diff_in_factors = self.prev_data[i]["factor"] - self.new_data[i]["factor"]
                diff_in_values = self.prev_data[i]["value"] - self.new_data[i]["value"]
                
                if abs(diff_in_factors * pi_factor) < 0.001:
                    bars_below_lim += 1
                
                
                self.data[i]["factor"] = self.prev_data[i]["factor"] - (diff_in_factors * pi_factor)
                self.data[i]["value"] = self.prev_data[i]["value"] - (diff_in_values * pi_factor)
                
            if bars_below_lim == len(self.data): #all bars done - stop animation!
                self.current_frame = self.animation_frames
                

        if self.current_frame < self.animation_frames:
            self._invalidate()
            return True
        else:
            self.data = copy.copy(self.new_data)
            self.prev_data = copy.copy(self.new_data)
            self._invalidate()
            return False

    def _invalidate(self):
        """Force redrawal of chart"""
        if self.window:    #this can get called before expose    
            alloc = self.get_allocation()
            rect = gtk.gdk.Rectangle(alloc.x, alloc.y, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)
            
    
    def _get_factors(self, data):
        """get's max value out of data and calculates each record's factor
           against it"""
        max_value = 0
        self.there_are_floats = False
        self.there_are_colors = False
        self.there_are_backgrounds = False
        
        for i in range(len(data)):
            max_value = max(max_value, data[i][1])
            if isinstance(data[i][1], float):
                self.there_are_floats = True #we need to know for the scale labels
                
            if len(data[i]) > 3 and data[i][2] != None:
                self.there_are_colors = True
                
            if len(data[i]) > 4 and data[i][3] != None:
                self.there_are_backgrounds = True
                
        
        res = []
        for i in range(len(data)):
            factor = data[i][1] / float(max_value) if max_value > 0 else 0
            
            res.append({"label": data[i][0],
                        "value": data[i][1],
                        "color": data[i][2] if len(data[i]) > 2 else None,
                        "background": data[i][3] if len(data[i]) > 3 else None,
                        "factor": factor
                        })
        
        return res, max_value
    
    
    def _bar_chart(self, context):
        rect = self.get_allocation()  #x, y, width, height        
        data, records = self.data, len(self.data)

        if not data:
            return

        # graph box dimensions
        graph_x = rect.x + 50  #give some space to scale labels
        graph_width = rect.width + rect.x - graph_x
        
        step = graph_width / float(records)
        if self.max_bar_width:
            step = min(step, self.max_bar_width)
            if self.collapse_whitespace:
                graph_width = step * records #no need to have that white stuff

        graph_y = rect.y
        graph_height = graph_y - rect.x + rect.height - 15
        
        max_size = graph_height - 15



        context.set_line_width(1)
        
        # TODO put this somewhere else - drawing background and some grid
        context.rectangle(graph_x - 1, graph_y, graph_width, graph_height)
        context.set_source_rgb(1, 1, 1)
        context.fill_preserve()
        context.stroke()

        #backgrounds
        if self.there_are_backgrounds:
            for i in range(records):
                if data[i]["background"] != None:
                    set_color(context, light[data[i]["background"]]);
                    context.rectangle(graph_x + (step * i), 0, step, graph_height)
                    context.fill_preserve()
                    context.stroke()

        context.set_line_width(1)
        context.set_dash ([1, 3]);
        set_color(context, dark[8])
        
        # scale lines
        stride = self.default_grid_stride if self.stretch_grid == False else int(graph_height / 4)
            
        for y in range(graph_y, graph_y + graph_height, stride):
            context.move_to(graph_x - 10, y)
            context.line_to(graph_x + graph_width, y)

        # and borders on both sides, so the graph doesn't fall out
        context.move_to(graph_x - 1, graph_y)
        context.line_to(graph_x - 1, graph_y + graph_height + 1)
        context.move_to(graph_x + graph_width, graph_y)
        context.line_to(graph_x + graph_width, graph_y + graph_height + 1)
        

        context.stroke()
        
        
        context.set_dash ([]);


        # labels
        set_color(context, dark[8]);
        for i in range(records):
            extent = context.text_extents(data[i]["label"]) #x, y, width, height
            context.move_to(graph_x + (step * i) + (step - extent[2]) / 2.0,
                            graph_y + graph_height + 13)
            context.show_text(data[i]["label"])

        # values for max min and average
        context.move_to(rect.x + 10, rect.y + 10)
        max_label = "%.1f" % self.max if self.there_are_floats else "%d" % self.max
        context.show_text(max_label)


        #flip the matrix vertically, so we do not have to think upside-down
        context.transform(cairo.Matrix(yy = -1, y0 = graph_height))

        # bars themselves
        for i in range(records):
            bar_size = graph_height * data[i]["factor"]

            #on animations we keep labels on top, so we need some extra space there
            bar_size = bar_size * 0.8 if self.values_on_bars and self.animate else bar_size * 0.9
                
            context.rectangle(graph_x + (step * i) + (step * 0.1),
                              0,
                              step * 0.8,
                              bar_size)

            color = data[i]["color"] or 1
            if self.cycle_colors:
                if color_count < records:
                    color = (i + 1) % color_count
                else:
                    color = i
                
            set_color(context, light[color])
            context.fill_preserve()    
            set_color(context, dark[color]);
            context.stroke()

        #values
        #flip the matrix back, so text doesn't come upside down
        context.transform(cairo.Matrix(yy = -1, y0 = 0))
        set_color(context, dark[8])        
        if self.values_on_bars:
            for i in range(records):
                label = "%.1f" % data[i]["value"] if self.there_are_floats else "%d" % data[i]["value"]
                extent = context.text_extents(label) #x, y, width, height
                
                bar_size = graph_height * data[i]["factor"]
                
                bar_size = bar_size * 0.8 if self.animate else bar_size * 0.9
                    
                vertical_offset = (step - extent[2]) / 2.0
                
                if self.animate or bar_size - vertical_offset < extent[3]:
                    graph_y = -bar_size - 3
                else:
                    graph_y = -bar_size + extent[3] + vertical_offset
                
                context.move_to(graph_x + (step * i) + (step - extent[2]) / 2.0,
                                graph_y)
                context.show_text(label)



        
    def _horizontal_bar_chart(self, context):
        rect = self.get_allocation()  #x, y, width, height
        data, records = self.data, len(self.data)
        
        # ok, start with labels - get the longest now
        # TODO - figure how to wrap text
        max_extent = 0
        for i in range(records):
            extent = context.text_extents(data[i]["label"]) #x, y, width, height
            max_extent = max(max_extent, extent[2])
            
        
        #push graph to the right, so it doesn't overlap, and add little padding aswell
        graph_x = int(rect.x + max_extent + 10)
        graph_width = int(rect.width + rect.x - graph_x - 40)

        graph_y = rect.y
        graph_height = graph_y - rect.x + rect.height
        
        
        step = graph_height / float(records) if records > 0 else 30
        if self.max_bar_width:
            step = min(step, self.max_bar_width)
            if self.collapse_whitespace:
                graph_height = step * records #resize graph accordingly
        
        max_size = graph_width - 15


        #now let's put the labels and align them right
        set_color(context, dark[8]);
        for i in range(records):
            extent = context.text_extents(data[i]["label"]) #x, y, width, height
            
            context.move_to(rect.x + max_extent - extent[2], rect.y + (step * i) + (step + extent[3]) / 2)
            context.show_text(data[i]["label"])
        
        context.stroke()        
        
        


        context.set_line_width(1)
        
        
        # TODO put this somewhere else - drawing background and some grid
        context.rectangle(graph_x - 1, rect.y, graph_width, graph_height)
        context.set_source_rgb(1, 1, 1)
        context.fill_preserve()
        context.stroke()


        context.set_line_width(1)
        context.set_dash ([1, 3]);

        set_color(context, dark[8])

        # scale lines        
        grid_stride = self.default_grid_stride if self.stretch_grid == False else int(graph_width / 4)
        for x in range(graph_x, graph_x + graph_width, grid_stride):
            context.move_to(x-1, graph_y)
            context.line_to(x-1, graph_y + graph_height)

        # and borders on both sides, so the graph doesn't fall out
        context.move_to(graph_x, graph_y)
        context.line_to(graph_x + graph_width, graph_y)
        context.move_to(graph_x, graph_y + graph_height)
        context.line_to(graph_x + graph_width, graph_y + graph_height)


        context.stroke()
        
        
        context.set_dash ([]);
        # bars themselves
        for i in range(records):
            context.rectangle(graph_x,
                              graph_y + (step * i) + step * 0.1,
                              (max_size * data[i]["factor"]),
                              step * 0.8)

            color = data[i]["color"] or 1
            if self.cycle_colors:
                if color_count < records:
                    color = (i + 1) % color_count
                else:
                    color = i
                
            set_color(context, light[color])
            context.fill_preserve()    
            set_color(context, dark[color]);
            context.stroke()
        

        #values
        set_color(context, dark[8])        
        if self.values_on_bars:
            for i in range(records):
                label = "%.1f" % data[i]["value"] if self.there_are_floats else "%d" % data[i]["value"]
                extent = context.text_extents(label) #x, y, width, height
                
                bar_size = max_size * data[i]["factor"]
                horizontal_offset = (step + extent[3]) / 2.0 - extent[3]
                
                if  bar_size - horizontal_offset < extent[2]:
                    label_x = graph_x + bar_size + horizontal_offset
                else:
                    label_x = graph_x + bar_size - extent[2] - horizontal_offset
                
                context.move_to(label_x, graph_y + (step * i) + (step + extent[3]) / 2.0)
                context.show_text(label)

        else:
            # values for max min and average
            context.move_to(graph_x + graph_width + 10, graph_y + 10)
            max_label = "%.1f" % self.max if self.there_are_floats else "%d" % self.max
            context.show_text(max_label)
        
        
    def _area_chart(self, context):
        rect = self.get_allocation()  #x, y, width, height        
        data, records = self.data, len(self.data)

        if not data:
            return

        # graph box dimensions
        graph_x = rect.x + 50  #give some space to scale labels
        graph_width = rect.width + rect.x - graph_x
        
        step = graph_width / float(records)
        graph_y = rect.y
        graph_height = graph_y - rect.x + rect.height - 15
        
        max_size = graph_height - 15



        context.set_line_width(1)
        
        # TODO put this somewhere else - drawing background and some grid
        context.rectangle(graph_x, graph_y, graph_width, graph_height)
        context.set_source_rgb(1, 1, 1)
        context.fill_preserve()
        context.stroke()

        context.set_line_width(1)
        context.set_dash ([1, 3]);


        #backgrounds
        if self.there_are_backgrounds:
            for i in range(records):
                if data[i]["background"] != None:
                    set_color(context, light[data[i]["background"]]);
                    context.rectangle(graph_x + (step * i), 1, step, graph_height - 1)
                    context.fill_preserve()
                    context.stroke()

            
        set_color(context, dark[8])
        
        # scale lines
        stride = self.default_grid_stride if self.stretch_grid == False else int(graph_height / 4)
            
        for y in range(graph_y, graph_y + graph_height, stride):
            context.move_to(graph_x - 10, y)
            context.line_to(graph_x + graph_width, y)

        # and borders on both sides, so the graph doesn't fall out
        context.move_to(graph_x - 1, graph_y)
        context.line_to(graph_x - 1, graph_y + graph_height + 1)
        context.move_to(graph_x + graph_width, graph_y)
        context.line_to(graph_x + graph_width, graph_y + graph_height + 1)
        

        context.stroke()
        
        
        context.set_dash ([]);

        # labels
        set_color(context, dark[8]);
        for i in range(records):
            if i % 5 == 0:
                context.move_to(graph_x + 5 + (step * i), graph_y + graph_height + 13)
                context.show_text(data[i]["label"])

        # values for max min and average
        context.move_to(rect.x + 10, rect.y + 10)
        max_label = "%.1f" % self.max if self.there_are_floats else "%d" % self.max
        context.show_text(max_label)


        context.rectangle(graph_x, graph_y, graph_width, graph_height + 1)
        context.clip()

        #flip the matrix vertically, so we do not have to think upside-down
        context.transform(cairo.Matrix(yy = -1, y0 = graph_height))


        set_color(context, dark[3]);
        # chart itself
        for i in range(records):
            if i == 0:
                context.move_to(graph_x, -10)
                context.line_to(graph_x, graph_height * data[i]["factor"] * 0.9)
                
            context.line_to(graph_x + (step * i) + (step * 0.5), graph_height * data[i]["factor"] * 0.9)

            if i == records - 1:
                context.line_to(graph_x  + (step * i) + (step * 0.5),  0)
                context.line_to(graph_x + graph_width, 0)
                context.line_to(graph_x + graph_width, -10)
                


        set_color(context, light[3])
        context.fill_preserve()    

        context.set_line_width(3)
        context.set_line_join (cairo.LINE_JOIN_ROUND);
        set_color(context, dark[3]);
        context.stroke()    
        




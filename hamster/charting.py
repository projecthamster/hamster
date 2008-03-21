"""Small charting library that enables you to draw simple bar and
horizontal bar charts. Some documentation might be coming

Author: toms.baugis@gmail.com
Licensed under LGPL - do whatever you want, and send me some cookies, if you
feel like it.
"""

import gtk

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
    def __init__(self, **args):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.data = None #start off with an empty hand
        
        """now see what we have in args!"""
        self.cycle_colors = "cycle_colors" in args and args["cycle_colors"] # defaults to false
        self.orient_vertical = "orient" not in args or args["orient"] == "vertical" # defaults to true
        
        self.max_bar_width = None
        if "max_bar_width" in args: self.max_bar_width = args["max_bar_width"]        
        self.collapse_whitespace = "collapse_whitespace" in args and args["collapse_whitespace"] #defaults to false
        
        self.stretch_grid = "stretch_grid" in args and args["stretch_grid"] == True #defaults to false
        
        
        #and some defaults
        self.default_grid_stride = 50
        
    def expose(self, widget, event): # expose is when drawing's going on
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        context.clip()
        
        if self.orient_vertical:
            self.bar_chart(context) 
        else:
            self.horizontal_bar_chart(context)

        return False

    def plot(self, data):
        self.data = data

        if self.window:    #this can get called before expose    
            alloc = self.get_allocation()
            rect = gtk.gdk.Rectangle(alloc.x, alloc.y, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)
        
    
    def bar_chart(self, context):
        rect = self.get_allocation()  #x, y, width, height        
        data, records = self.data, len(self.data)

        if not data:
            return

        # graph box dimensions
        graph_x = rect.x + 50  #give some space to scale labels
        graph_width = rect.width + rect.x - graph_x
        
        step = graph_width / records
        if self.max_bar_width:
            step = min(step, self.max_bar_width)
            if self.collapse_whitespace:
                graph_width = step * records #no need to have that white stuff

        graph_y = rect.y
        graph_height = graph_y - rect.x + rect.height - 15
        
        max_size = graph_height - 15



        context.set_line_width(1)
        
        
        #find max, so we know
        max_value = 0.1
        for i in data:
            max_value = max(max_value, i[1] * 1.0)
        

        # TODO put this somewhere else - drawing background and some grid
        context.rectangle(graph_x - 1, graph_y, graph_width, graph_height)
        context.set_source_rgb(1, 1, 1)
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
        # bars themselves
        for i in range(records):
            context.rectangle(graph_x + (step * i),
                              graph_y + graph_height - (graph_height * (data[i][1] / max_value)),
                              step * 0.8,
                              (graph_height * (data[i][1] / max_value)))

            color = 1
            if self.cycle_colors:
                if color_count < records:
                    color = (i + 1) % color_count
                else:
                    color = i
                
            set_color(context, light[color])
            context.fill_preserve()    
            set_color(context, dark[color]);
            context.stroke()
        
        # labels
        set_color(context, dark[8]);
        for i in range(records):
            context.move_to(graph_x + 5 + (step * i), graph_y + graph_height + 15)
            context.show_text(data[i][0])

        # values for max minn and average
        context.move_to(rect.x + 10, rect.y + 10)
        context.show_text(str(max_value))




    def horizontal_bar_chart(self, context):
        rect = self.get_allocation()  #x, y, width, height
        data, records = self.data, len(self.data)
        
        # ok, start with labels - get the longest now
        # TODO - figure how to wrap text
        max_extent, max_value = 0, 0.1
        for i in range(records):
            extent = context.text_extents(data[i][0]) #x, y, width, height
            max_extent = max(max_extent, extent[2])
            max_value = max(max_value, data[i][1] * 1.0)
            
        
        #push graph to the right, so it doesn't overlap, and add little padding aswell
        graph_x = int(rect.x + max_extent + 10)
        graph_width = int(rect.width + rect.x - graph_x - 40)

        graph_y = rect.y
        graph_height = graph_y - rect.x + rect.height
        
        
        step = graph_height / records if records > 0 else 30
        if self.max_bar_width:
            step = min(step, self.max_bar_width)
            if self.collapse_whitespace:
                graph_height = step * records #resize graph accordingly
        
        max_size = graph_width - 15


        #now let's put the labels and align them right
        set_color(context, dark[8]);
        for i in range(records):
            extent = context.text_extents(data[i][0]) #x, y, width, height
            
            context.move_to(rect.x + max_extent - extent[2], rect.y + (step * i) + (step + extent[3]) / 2)
            context.show_text(data[i][0])
        
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
                              (max_size * (data[i][1] / max_value)),
                              step * 0.8)

            color = 1
            if self.cycle_colors:
                if color_count < records:
                    color = (i + 1) % color_count
                else:
                    color = i
                
            set_color(context, light[color])
            context.fill_preserve()    
            set_color(context, dark[color]);
            context.stroke()
        

        # values for max minn and average
        context.move_to(graph_x + graph_width + 10, graph_y + 10)
        context.show_text(str(max_value))
        
        


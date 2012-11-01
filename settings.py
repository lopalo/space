from os import path
from random import choice

Root = path.dirname(__file__)

minimum_window_size = (1000, 600)
density = 20
G = 1000
frequency = 30
default_position = (40.0, 40.0)
default_planet_radius = 30
max_planet_radius = 50 # for adding
max_mass = 4000
reflect_factor = 0.5
break_speed = 300 # plantes speed after break (pixels/second)
captured_speed_factor = 3
glow_factor = 0.02
glow_radius = 300
minimum_wormhole_radius = 20
maximum_wormhole_radius = 80
on_shadows = True

#effects
effects_path = path.join(Root, 'images', 'scene', 'effects')
bang_components_count = 2
bang_image = 'bang.png'
effects_update_time = 0.017 #the time between updating of effects in seconds

planet_images_path = path.join(Root, 'images', 'scene', 'planets')
planet_images = (
    'planet1.png',
    'planet2.png',
    'planet3.png',
    'planet4.png',
    'planet5.png',
    'planet6.png',
    'planet7.png',
    'planet8.png',
    'planet9.png',
    'planet10.png',
    )
collided_image = 'fire_planet.png'

background_images_path = path.join(Root, 'images', 'scene', 'backgrounds')
background_image = '84.jpg'

save_file = 'save.json' #should be in the json format

#interface images
interface_images_path = path.join(Root, 'images', 'interface')
# set pixmap in the center of the cursor if a second parameter is True
cursor = ('arrow.png', False,)
take_cursor = ('hand.png', True,)
taken_cursor = ('taken.png', True,)
add_cursor = ('add1.png', False,)
add_cursor_disabled = ('add1_disabled.png', False,)
del_cursor = ('del1.png', False,)
add_wh_cursor = ('add_wh.png', True,)
add_wh_cursor_disabled = ('add_wh_disabled.png', True,)
break_cursor = ('break1.png', False)
add_button_image = 'add2.png'
del_button_image = 'del2.png'
break_button_image = 'break2.png'
save_button_image = 'save.png'
load_button_image = 'load.png'
add_wh_button_image = 'add_wh.png'


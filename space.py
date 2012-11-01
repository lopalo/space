import sys
from os import path
from time import time
from math import hypot
from random import choice
import json
from PyQt4.Qt import Qt
from PyQt4.QtGui import *
from PyQt4.QtCore import QTimer, QSize
from . import settings
from .planet import Planet
from .space_objects import WormHole
from .utils import frame_rate

loading_interval = 1

x_coord_panel_elements = {
    'del_button': 15,
    'add_frame': 85,
    'add_button': 95,
    'combobox': 160,
    'pl_radius': 210,
    'break_button': 315,
    'total_mass': 565,
    'add_wh_button': 395,
    'wh_radius': 460,
    'add_wh_frame': 385,
    'save_button': 755,
    'load_button': 825,
}

frames_lengths = {
    'add_frame': 220,
    'add_wh_frame': 170,
}

hot_keys = {
    '1': 'del',
    '2': 'add',
    '3': 'break',
    '4': 'add_wh',
    '8': 'save',
    '9': 'load',
}


class Pixmap(QPixmap):

    def __init__(self, img_path):
        error_text = "file '{0}' doesn't exist".format(img_path)
        assert path.isfile(img_path), error_text
        super(Pixmap, self).__init__(img_path)


class Window(QWidget):
    last_loading = 0
    timers = []

    def __init__(self, app):
        super(QWidget, self).__init__()
        self.app = app
        self.action = None
        self.setStyleSheet(
            "QWidget {background: #111113; padding: 3px; color: white} \
            QGraphicsView, QPushButton , QLabel, QComboBox, QFrame \
            {border: 2px solid white; border-radius: 6px}"
        )
        w_size = settings.minimum_window_size
        self.background = background = Pixmap(
            path.join(
                settings.background_images_path,
                settings.background_image)
        )
        H = background.height()
        W = background.width()
        assert W >= w_size[0], W
        assert H >= w_size[1], H
        assert W > H, 'bad image proportion'
        self.setMinimumSize(*w_size)

        self.scene = scene = Scene(self)
        self.g_view = g_view = QGraphicsView(scene, self)
        g_view.setRenderHint(QPainter.Antialiasing, True)
        g_view.setMouseTracking(True)

        self.set_control_panel()
        Planet.setup(self, scene)
        self.set_sizes()

    def resizeEvent(self, event):
        self.set_sizes()

    def set_sizes(self):
        W, H = float(self.width()), float(self.height())
        gv_size = (W - 30, H - 85)
        s_size = (W - 40, H - 95)
        self.g_view.setSceneRect(0, 0, *s_size)
        self.g_view.setGeometry(15, 77, *gv_size)
        Planet.set_max_pos(*s_size)

        if hasattr(self, 'bckg_item'): self.scene.removeItem(self.bckg_item)
        bckg = self.background
        if (W / H) > (float(bckg.width()) / float(bckg.height())):
            new_bckg = bckg.scaledToWidth(W)
        else:
            new_bckg = bckg.scaledToHeight(H)
        new_bckg = new_bckg.copy(0, 0, W, H)
        self.bckg_item = self.scene.addPixmap(new_bckg)
        self.bckg_item.setZValue(-1)

    def set_control_panel(self):
        scene = self.scene
        x_coord = x_coord_panel_elements

        #set_frames
        self.frames = frames = dict()
        for f_name in ('add_frame', 'add_wh_frame'):
            w = frames[f_name] = QFrame(self)
            x = x_coord[f_name]
            w.setGeometry(x, 8, frames_lengths[f_name], 60)

        #set buttons
        self.click_buttons = ('save', 'load',)
        self.buttons = dict()
        for action in ('del', 'add', 'break', 'save', 'load', 'add_wh'):
            pixmap = Pixmap(path.join(
                settings.interface_images_path,
                getattr(settings, action + '_button_image')
            ))
            button = self.buttons[action] = QPushButton(QIcon(pixmap), '', self)
            button.setIconSize(QSize(32, 32))
            for k, v in hot_keys.items():
                if v == action: break
            if hot_keys[k] != action: k = ''
            button.setText(k)
            x = x_coord[action + '_button']
            button.setGeometry(x, 18, 60, 40)
            button.setFocusPolicy(0)
            if not action in self.click_buttons:
                button.setCheckable(True)
                button.toggled.connect(self.make_button_handler(action))
            else:
                button.clicked.connect(getattr(self, action))

        #set labels
        pl_radius = str(settings.default_planet_radius)
        self.pl_radius_label = QLabel('radius: ' + pl_radius, self)
        x = x_coord['pl_radius']
        self.pl_radius_label.setGeometry(x, 18, 83, 40)

        text = 'total mass: 0 / ' + str(settings.max_mass)
        self.total_mass_label = QLabel(text, self)
        x = x_coord['total_mass']
        self.total_mass_label.setGeometry(x, 18, 180, 40)

        min_wh_rad = str(settings.minimum_wormhole_radius)
        self.wh_radius_label = QLabel('radius: ' + min_wh_rad, self)
        x = x_coord['wh_radius']
        self.wh_radius_label.setGeometry(x, 18, 83, 40)

        #set combobox
        self.combobox = combobox = QComboBox(self)
        combobox.addItem('')
        for i in settings.planet_images:
            icon = QIcon(Pixmap(path.join(settings.planet_images_path, i)))
            combobox.addItem(icon, '')
        x = x_coord['combobox']
        combobox.setGeometry(x, 18, 45, 40)

    def make_button_handler(self, action):
        buttons = self.buttons
        frames = self.frames
        f_name = action + '_frame'
        def toggled(state):
            if state:
                for a_name, b in buttons.items():
                    if a_name != action:
                        b.setChecked(False)
                self.action = action
                self.update_cursor()
                buttons[action].setStyleSheet('background: #4e4e5a')
                if f_name in frames:
                    self.frames[f_name].setStyleSheet('border-color: #1e90ff')
                if action == 'add':
                    self.combobox.setEnabled(True)
            else:
                self.action = None
                buttons[action].setStyleSheet('background: #111113')
                if f_name in frames:
                    self.frames[f_name].setStyleSheet('border-color: white')
                if action == 'add':
                    self.combobox.setEnabled(False)
        return toggled

    def animate_click(self, but_name):
        but = self.buttons[but_name]
        but.setStyleSheet('background: #4e4e5a')
        def callback():
            but.setStyleSheet('background: #111113')
            self.timers.remove(timer)
        timer = QTimer()
        self.timers.append(timer)
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        timer.start(200)


    def save(self):
        self.animate_click('save')
        file_path = path.join(settings.Root, settings.save_file)
        planets = [pl.to_dict() for pl in Planet.planets]
        wormholes = [wh.to_dict() for wh in self.scene.wh_pair]
        data = dict(planets=planets, wormholes=wormholes)
        with open(file_path, 'wt') as f:
            json.dump(data, f)

    def load(self):
        self.animate_click('load')
        if time() - self.last_loading < loading_interval: return
        file_path = path.join(settings.Root, settings.save_file)
        if not path.isfile(file_path): return
        with open(file_path, 'rt') as f:
            data = json.load(f)
            pl_list, wh_list = data['planets'], data['wormholes']
            p_images = settings.planet_images
            for pl in pl_list:
                p_img = pl['image_name']
                if not p_img in p_images and p_img != settings.collided_image:
                    return
            def get_cb(pl):
                def callback():
                    Planet(**pl)
                return callback
            def create():
                for pl in pl_list:
                    img_path = path.join(
                        settings.planet_images_path, pl['image_name']
                    )
                    pl['pixmap'] = pixmap = Pixmap(img_path)
                    Planet.make_inflation(
                        pixmap, pl['radius'], pl['position'], get_cb(pl)
                    )
                for wh in wh_list:
                    self.scene.add_wormhole(**wh)
            wh_pair = self.scene.wh_pair
            if wh_pair:
                while wh_pair:
                    wh_pair[0].delete()
            if Planet.planets:
                while Planet.planets:
                    if len(Planet.planets) == 1:
                        Planet.planets[0].make_collapsing(create)
                    else:
                        Planet.planets[0].make_collapsing()
                    Planet.planets[0].delete()
            else:
                create()
        self.last_loading = time()

    def set_cursor(self, cursor):
        img_name, in_center = getattr(settings, cursor)
        cursor_img = Pixmap(
            path.join(settings.interface_images_path, img_name)
        )
        if in_center:
            cursor = QCursor(cursor_img, -1, -1)
        else:
            cursor = QCursor(cursor_img, 0, 0)
        self.app.setOverrideCursor(cursor)

    def update_cursor(self):
        scene = self.scene
        a = self.action
        if a == 'del':
            self.set_cursor('del_cursor')
        elif a == 'add':
            r = scene.pl_radius
            if Planet.check_adding(r) and scene.check_adding():
                self.set_cursor('add_cursor')
            else:
                self.set_cursor('add_cursor_disabled')
        elif a == 'break':
            self.set_cursor('break_cursor')
        elif a == 'add_wh':
            pair = scene.wh_pair
            if len(pair) == 2:
                self.set_cursor('add_wh_cursor_disabled')
                return
            r = scene.wh_radius
            pos = scene.cursor_pos
            if len(pair) == 1:
                wh = pair[0]
                if not scene.check_wormhole_position(r, pos, wh):
                    self.set_cursor('add_wh_cursor_disabled')
                    return
            if not scene.check_wormhole_position(r, pos):
                self.set_cursor('add_wh_cursor_disabled')
            else:
                self.set_cursor('add_wh_cursor')
        else:
            pos = scene.cursor_pos
            for obj in Planet.planets + scene.wh_pair:
                dist = hypot(pos[0] - obj.position[0], pos[1] - obj.position[1])
                if dist <= obj.radius:
                    if obj.captured:
                        self.set_cursor('taken_cursor')
                    else:
                        self.set_cursor('take_cursor')
                    break
            else:
                self.set_cursor('cursor')


class Scene(QGraphicsScene):
    cursor_pos = (0.0, 0.0)
    wh_pair = list()

    def __init__(self, window):
        super(Scene, self).__init__()
        self.window = window
        self.hot_keys_enabled = True

    def check_adding(self):
        pos = self.cursor_pos
        for pl in Planet.planets:
            radius = self.pl_radius
            min_dist = radius + pl.radius
            dist = hypot(pos[0] - pl.position[0], pos[1] - pl.position[1])
            if dist < min_dist: return False
        return True

    def mouseMoveEvent(self, event):
        super(Scene, self).mouseMoveEvent(event)
        point = event.scenePos()
        pos = (point.x(), point.y())
        self.cursor_pos = pos

    def mousePressEvent(self, event):
        super(Scene, self).mousePressEvent(event)
        point = event.scenePos()
        self.cursor_pos = pos = (point.x(), point.y())
        a = self.window.action
        if a == 'add':
            if not self.check_adding(): return
            p_images = settings.planet_images
            index = self.window.combobox.currentIndex()
            if index == 0:
                p_image = choice(p_images)
            else:
                index -= 1
                p_image = p_images[index]
            radius = self.pl_radius
            pixmap = Pixmap(path.join(settings.planet_images_path, p_image))
            def callback():
                Planet(pixmap, p_image, radius, list(pos))
            Planet.make_inflation(
                pixmap, radius, pos, callback
            )
        elif a == 'add_wh':
            radius = self.wh_radius
            self.add_wormhole(radius, pos)

    def add_wormhole(self, radius, pos):
        if len(self.wh_pair) > 1: return
        if self.wh_pair:
            ret = self.check_wormhole_position(radius, pos, self.wh_pair[0])
        else:
            ret = self.check_wormhole_position(radius, pos)
        if not ret: return
        wh = WormHole(radius, pos)
        self.wh_pair.append(wh)
        self.addItem(wh)

    def check_wormhole_position(self, r, pos, other=None):
        max_x, max_y = Planet.max_x - r, Planet.max_y - r
        if r > pos[0] or r > pos[1] or max_x < pos[0] or max_y < pos[1]:
            return False

        if other:
            min_dist = r + other.radius
            o_pos = other.position
            x, y = o_pos[0] - pos[0], o_pos[1] - pos[1]
            dist = hypot(x, y)
            if min_dist > dist:
                return False
        return True

    def update_wormholes(self, time_delta):
        assert len(self.wh_pair) <= 2

        pair = self.wh_pair
        for wh in tuple(pair):
            if not self.check_wormhole_position(
                wh.radius, wh.position, wh.other(pair)
            ):
                wh.delete()
                continue
            wh._update(pair, Planet.planets, self.window.bckg_item, time_delta)


    @property
    def pl_radius(self):
        return int(self.window.pl_radius_label.text().split(':')[1])

    @property
    def wh_radius(self):
        return int(self.window.wh_radius_label.text().split(':')[1])

    def wheelEvent(self, event):
        a = self.window.action
        if a == 'add':
            new_radius = self.pl_radius + event.delta() / 120
            new_radius = min(max(new_radius, 1), settings.max_planet_radius)
            self.window.pl_radius_label.setText('radius: ' + str(new_radius))
        elif a == 'add_wh':
            min_rad = settings.minimum_wormhole_radius
            max_rad = settings.maximum_wormhole_radius
            new_radius = self.wh_radius + event.delta() / 120
            new_radius = min(max(new_radius, min_rad), max_rad)
            self.window.wh_radius_label.setText('radius: ' + str(new_radius))
        self.window.update_cursor()

    def keyPressEvent(self, event):
        text = str(event.text())
        if text in hot_keys and self.hot_keys_enabled:
            action = hot_keys[text]
            button = self.window.buttons[action]
            if not action in self.window.click_buttons:
                if button.isChecked():
                    button.setChecked(False)
                else:
                    button.setChecked(True)
            else:
                button.clicked.emit(True)


def main():
    QApplication.setGraphicsSystem('raster')
    app = QApplication(sys.argv)
    window = Window(app)

    @frame_rate
    def update():
        last_time = getattr(window, 'last_time', time())
        time_delta = time() - last_time
        window.last_time = time()
        Planet.action_loop(time_delta)
        window.scene.update_wormholes(time_delta)
        window.update_cursor()
    interval = 1000 / settings.frequency
    timer = QTimer()
    timer.timeout.connect(update)
    timer.start(interval)

    #need for caching
    Pixmap(path.join(settings.effects_path, settings.bang_image))
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

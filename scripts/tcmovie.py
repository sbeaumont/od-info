import os
from math import cos, sin, radians

from moviepy.editor import *
from visualize import Visualizer, COLORS, Point
from odinfo.opsdata import Database
from PIL import ImageFont
from odinfo.domain import realm_of_dom
from odinfo.config import OUT_DIR

from odinfo.config import DATABASE


def centers_for(num_factions, distance):
    def polar_to_cartesian(r, theta):
        x = r * cos(radians(theta))
        y = r * sin(radians(theta))
        return round(x), round(y)

    result = list()
    for i in range(num_factions):
        angle = (i * int(360 / num_factions))
        result.append(polar_to_cartesian(distance, angle))
    return result


def visualise_points(list_of_points):
    boundaries = Visualizer.boundaries(list_of_points, padding=50)
    vis = Visualizer(boundaries, scale=2)
    for p in list_of_points:
        vis.draw_circle(Point(*p))
    vis.show()


def get_tc_lines(db):
    return db.query('SELECT * FROM TownCrier ORDER BY timestamp ASC')


def export_video():
    def slide_key(name):
        return int(name[len('out/tcmovie/tcmovie-'):-4])
    img_clips = []
    path_list = []
    # accessing path of each image
    for image in os.listdir('out/tcmovie/'):
        if image.endswith(".png"):
            path_list.append(os.path.join('out/tcmovie/', image))
    pass
    # creating slide for each image
    for img_path in sorted(path_list, key=slide_key):
        slide = ImageClip(img_path, duration=0.05)
        img_clips.append(slide)
    # concatenating slides
    video_slides = concatenate_videoclips(img_clips, method='compose')
    # exporting final video
    video_slides.write_videofile("out/tc_movie.mp4", fps=24)


def draw_realms(db, realms, event=None, file_name=None):
    vis = Visualizer((-600, -600, 600, 600))
    font = ImageFont.truetype('SourceCodePro-Regular', 20)
    if event:
        vis.text(point=Point(0, 0), msg=event['timestamp'], font=font, fill=COLORS[6], anchor='mm')
    for realm in realms.values():
        circle_size = realm.ratio * 100
        vis.draw_circle(realm.xy, size=circle_size, fill=COLORS[6])
    for realm in realms.values():
        circle_size = realm.ratio * 100
        vis.draw_circle(realm.xy, size=circle_size, outline=COLORS[4], width=3)
    for realm in realms.values():
        realm_label = f'{str(realm.nr)}\n{str(round(realm.ratio * 100, 2))}'
        vis.text(point=realm.xy, msg=realm_label, font=font, fill=COLORS[7], anchor='mm')
    if event:
        origin = realm_of_dom(db, event['origin'])
        target = realm_of_dom(db, event['target'])
        hit_size = event['amount']
        vis.draw_line((realms[origin].xy, realms[target].xy), color=COLORS[3], width=hit_size // 10)

    if file_name:
        vis.save(file_name)
    else:
        vis.show()


class Realm(object):
    def __init__(self, nr, xy, size=10000):
        self.nr = nr
        self.size = size
        self.original_size = size
        self.xy = xy

    def init_size(self, size):
        self.size = size
        self.original_size = size

    @property
    def ratio(self):
        return self.size / self.original_size


def go():
    db = Database()
    db.init(DATABASE)
    realms = dict()
    i = 0
    for x, y in centers_for(14, 400):
        realms[i] = Realm(i, Point(x, y))
        i += 1
    realms[0].init_size(100000)

    invasions = [line for line in get_tc_lines(db) if line['event_type'] == 'invasion']
    volg_nr = 1
    for event in [inv for inv in invasions if inv is not None]:
        try:
            assert event['origin'], f"Origin of event {event} should not be None"
            origin = realm_of_dom(db, event['origin'])
            assert event['target'], f"Target of event {event} should not be None"
            target = realm_of_dom(db, event['target'])
            assert event['amount'], f"Amount of event {event} should not be None"
            hit_size = event['amount']
            realms[target].size -= hit_size
            realms[origin].size += hit_size
            file_name = f'out/tcmovie/tcmovie-{volg_nr}.png'
            draw_realms(db, realms, event, file_name)
            print("Printed event", volg_nr)
        except (AssertionError, TypeError):
            pass
        volg_nr += 1
    draw_realms(db, realms)


def connect_audio():
    audio = AudioFileClip(f'{OUT_DIR}/follow-the-leader-action-trailer-glitch-intro-146760.mp3')
    video = VideoFileClip(f'{OUT_DIR}/tc_movie.mp4')
    video = video.subclip(10)
    video_with_audio = video.set_audio(audio)
    print(video_with_audio.audio)
    video_with_audio.write_videofile(
        "out/tc_movie_audio.mp4",
        codec='libx264',
        audio_codec='aac',
        temp_audiofile='temp-audio.m4a',
        remove_temp=True, fps=24)


if __name__ == '__main__':
    print("Generating frames...")
    go()
    print("Exporting video...")
    export_video()
    print("Attaching audio...")
    connect_audio()

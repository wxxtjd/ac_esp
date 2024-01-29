import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QTimer, QRect
import memreader

class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.i = 0

        #적 위치를 위한 버퍼
        self.screen_enemy_buffer = {}
        self.box_buffer = {}

        # 전체 화면으로 설정
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setGeometry(0, 0, 2560, 1600)

        # 박스를 표시할 QLabel 생성
        self.box_label = QLabel(self)
        self.box_label.setGeometry(100, 100, 200, 200)  # 초기 위치 및 크기 설정

        # 오버레이 배경 투명하게 설정
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 타이머 생성 및 연결
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateBox)
        self.timer.start(20)  # 1000밀리초 (1초) 마다 타이머 이벤트 발생

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 오버레이 배경을 투명 검정으로 그리기
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        #적 이름 리스트
        enemy_name_list = list(self.box_buffer.keys())

        for name in enemy_name_list:

            #박스
            box, draw_box, line_x, line_y = self.box_buffer[name]
            hp = self.screen_enemy_buffer[name]["HP"]

            #살아있는 적만 표시
            if hp > 0 and draw_box:
                #박스 그리기
                self.drawBox(painter, box.geometry(), hp)
                self.drawLine(painter, line_x, line_y+10, hp)

    def MakeBox(self, w=460, h=920, min_w=10, min_h=20, min_a=2):
        enemy_names = self.screen_enemy_buffer.keys()
        for enemy_name in enemy_names:

            #적 위치/이름/거리 등
            enemy = self.screen_enemy_buffer[enemy_name]
            x = enemy["X"]
            y = enemy["Y"]

            name = enemy_name
            distance = enemy["Distance"]

            distance = (0.94)**distance+0.1

            #박스의 요소(너비, 높이 등)
            box_w = max(w * distance, min_w)
            box_h = max(h * distance, min_h)
            a = max(200 * distance, min_a)

            box = QLabel(self)
            box.setGeometry(int(x-a), int(y-a), int(box_w), int(box_h))

            #화면에서 벗어나면 그리지 않음
            if (0 < x and x < 2560) and (0 < y and y < 1600): draw_box = True
            else: draw_box = False

            self.box_buffer[name] = (box, draw_box, int(x), int(y))

            if len(self.box_buffer) > len(enemy_names):
                first_name = list(self.box_buffer.keys())[0]
                del self.box_buffer[first_name]
            
    def drawBox(self, painter, rect, hp):
        g = int(2.55*hp)
        pen = QPen(QColor(255-g, g, 0), 2, Qt.SolidLine)  # 선의 색상, 굵기, 스타일 설정
        painter.setPen(pen)
        painter.drawRect(rect)

    def drawLine(self, painter, x, y, hp):
        g = int(2.55*hp)
        pen = QPen(QColor(255-g, g, 0), 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawLine(2560//2, 1600, x, y)

    def updateBox(self):
        view_matrix = memreader.GetViewMatrix()
        entities = memreader.GetEntityList()
        myplayer = memreader.GetMyInfo()
        screen_entity_dict = memreader.World2Screen(entities, view_matrix)
        entity_distance_dict = memreader.CalcDistance(myplayer, entities)
        entity_names = screen_entity_dict.keys()
        
        for entity_name in entity_names:
            entity_distance = entity_distance_dict[entity_name]
            entity_x = screen_entity_dict[entity_name][0]
            entity_y = screen_entity_dict[entity_name][1]
            
            for entity in entities:
                if entity["Name"] == entity_name:
                    entity_hp = entity["HP"]

            self.screen_enemy_buffer[entity_name] = {"X":entity_x, "Y":entity_y, "Distance":entity_distance, "HP":entity_hp}

            if len(self.screen_enemy_buffer) > len(entity_names):
                first_name = list(self.screen_enemy_buffer.keys())[0]
                del self.screen_enemy_buffer[first_name]

        self.MakeBox()

        self.update()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    overlay = Overlay()
    overlay.show()
    sys.exit(app.exec_())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
##Copyright 2009, 2010 Владимир Суханов 
##
#from OCC import STEPControl, StlAPI, IGESControl, TopoDS, BRep, BRepTools
#from OCC.AIS import AIS_Shape
from OCC.BRepBuilderAPI import *
from OCC.BRepPrimAPI import *
from OCC.BRepPrim import *
from OCC.gp import *
#from OCC.KBE.TypesLookup import ShapeToTopology
from OCC.KBE.types_lut import ShapeToTopology
import psycopg2
from regim import *
from utils import *
from liblas import *
import os, time
from math import *
from inpLAS import *
from random import random

def SaveProt(self):
    """ Сохранение протокола в файле """
    global txtWin
    wildcard = u"Файлы протокола (*.log)|*.log|"     \
               u"Все файлы (*.*)|*.*"
    dlg = wx.FileDialog(
        self.msgWin, message="Сохранить протокол в ...", defaultDir=os.getcwd(), 
        defaultFile="log.log", wildcard=wildcard, style=wx.SAVE
        )
    dlg.SetFilterIndex(1)
    if dlg.ShowModal() == wx.ID_OK:
        fileName = dlg.GetPath()
        self.msgWin.SaveFile(fileName)
    dlg.Destroy()
    
def CLine(self):
    """Рисование отрезка"""
    #self.canva.SetTogglesToFalse(event)
    self.canva.MakeLine = True
    self.canva.MakePLine = False
    self.canva.GumLine = True
    self.canva.lstPnt = []
    self.SetStatusText("Отрезок. Дай начало", 0)
    self._refreshui()
    #if not (self.canva._3dDisplay.Context.HasOpenedContext()):
    #    self.canva._3dDisplay.Context.OpenLocalContext(True)    #False

def PLine(self):
    """ Рисование ломаной """
    #self.canva.SetTogglesToFalse(event)
    self.canva.MakePLine = True
    self.canva.MakeLine = False
    self.canva.GumLine = True
    self.canva.lstPnt = []
    self.canva.tmpEdge = None
    self.SetStatusText("Полилиния. Дай начало", 0)
    self._refreshui()
    #if not (self.canva._3dDisplay.Context.HasOpenedContext()):
    #    self.canva._3dDisplay.Context.OpenLocalContext(True,True,True,True)    #False

def CAxis(self):
    """ Рисование длинных осей """
    edge = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0),
                        gp_Pnt(0, 10000, 0))
    self.canva._3dDisplay.DisplayColoredShape(edge.Edge(), 'CYAN')            
    edge = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0),
                        gp_Pnt(10000, 0, 0))
    self.canva._3dDisplay.DisplayColoredShape(edge.Edge(), 'CYAN')       
    edge = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0),
                        gp_Pnt(0, 0, 10000))
    self.canva._3dDisplay.DisplayColoredShape(edge.Edge(), 'CYAN')

def CreateDB(self): 
    """ Создание элементов в базе данных PostGIS """ 
    # Топография дневной поверхности      
    n = 5       # число уровней изолиний
    X00 = 5000  # центр изолиний
    Y00 = 4750
    Cnt = 0
    DLT_l = 15  # приращение сегмента
    DLT_h = 5   # приращение отметки
    D2_D1 = 0.5 # эксцентриситет
    R = 50      # расстояние между горизонталями в плане
    D10 = 50    # начальный диаметр
    Z0 = 200    # начальная отметка
    t00 = time.time()
    conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
    curs = conn.cursor()
    curs.execute("DELETE FROM topograph")
    for i in range(0, n):
        #
        D1 = D10 + i * R
        Z = Z0 - (i * DLT_h)
        m = int(3.14 * D1 / DLT_l) + 1
        D_Ugol = 6.28 / (m - 1)
        geom = "GeomFromEWKT('SRID=-1;LINESTRING("
        for j in range(0, m):
            fi = j * D_Ugol
            X = X00 + D1 * cos(fi)
            Y = Y00 + D1 * sin(fi) * D2_D1
            geom = geom + "%.0f %.0f %.0f" % (X, Y, Z)
            if (j < (m - 1)):
                geom = geom + ","
            Cnt = Cnt + 1
        geom = geom + ")')"
        #print geom
        query = "INSERT INTO topograph (heigth,coord_sys,geom) VALUES (" + str(Z) + ",1," + geom + ");"  
        #print query
        curs.execute(query)
    conn.commit()  
    curs.close()
    conn.close() 
#    self.SetStatusText("Готово", 0)
    # Горизонты и бровки и тела
    n = 5       # число горизонтов
    X00 = 5000  # центр
    Y00 = 5000  #
    Cnt = 0     #
    Hust = 15   # высота уступа
    DLT_l = 5   # приращение по длине сегмента
    D2_D1 = 0.5 # эксцентриситет
    R = 50      # ширина площадки
    D10 = 150   # начальный радиус
    Z0 = - 100   # начальная отметка
    t00 = time.time()
    conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
    curs = conn.cursor()
    curs.execute("DELETE FROM body")
    curs.execute("DELETE FROM edge")
    curs.execute("DELETE FROM dril_pars")
    curs.execute("DELETE FROM drills")
    curs.execute("DELETE FROM horizons WHERE id_hor>3")
        
    for i in range(0, n):        # По горизонтам
        D1 = D10 + i * R
        Z = Z0 + (i * Hust)
        self.SetStatusText("Создаается горизонт" + str(Z), 2)
        query = "INSERT INTO horizons (id_hor,point,h_ledge,description) VALUES (default," + "%.0f, %.0f" % (Z, Hust) + ", 'Tester') RETURNING id_hor;"  
        curs.execute(query)     #hor
        id_hor = curs.fetchone()[0]
        #print('id_hor=',id_hor)
        # Верхняя бровка
        m = int(3.14 * D1 / DLT_l) + 1
        D_Ugol = 6.28 / (m - 1)
        geom = "GeomFromEWKT('SRID=-1;LINESTRING("
        for j in range(0, m):
            fi = j * D_Ugol
            X = X00 + D1 * cos(fi)
            Y = Y00 + D1 * sin(fi) * D2_D1
            geom = geom + "%.0f %.0f %.0f" % (X, Y, Z)
            if (j < (m - 1)):
                geom = geom + ","
            Cnt = Cnt + 1
        geom = geom + ")')"
        #print geom
        query = "INSERT INTO edge (hor,edge_type,geom) VALUES (" + str(id_hor) + ",2," + geom + ");"  
        #print query
        curs.execute(query)
        # Нижняя бровка
        geom = "GeomFromEWKT('SRID=-1;LINESTRING("
        D2 = D1 + R - Hust / 2
        for j in range(0, m):
            fi = j * D_Ugol
            X = X00 + D2 * cos(fi)
            Y = Y00 + D2 * sin(fi) * D2_D1
            geom = geom + "%.0f %.0f %.0f" % (X, Y, Z)
            if (j < (m - 1)):
                geom = geom + ","
            Cnt = Cnt + 1
        geom = geom + ")')"
        #print geom
        query = "INSERT INTO edge (hor,edge_type,geom) VALUES (" + str(id_hor) + ",1," + geom + ");"  
        #print query
        curs.execute(query)
        # Рудные тела
        geom = "GeomFromEWKT('SRID=-1;LINESTRING("
        D2 = D1 + R - Hust / 2
        for j in range(0, m / 2):
            fi = j * D_Ugol
            X = X00 + D2 * cos(fi)
            Y = Y00 + D2 * sin(fi) * D2_D1
            geom = geom + "%.0f %.0f %.0f," % (X, Y, Z)
            #if (j < (m-1)):
            #    geom = geom + ","
            Cnt = Cnt + 1
        D2 = D2 + 3 * R
        for j in range(0, m / 2):
            fi = (m / 2 - j) * D_Ugol
            X = X00 + D2 * cos(fi)
            Y = Y00 + D2 * sin(fi) * D2_D1
            geom = geom + "%.0f %.0f %.0f" % (X, Y, Z)
            if (j < (m / 2 - 1)):
                geom = geom + ","
            Cnt = Cnt + 1
        geom = geom + ")')"
        #print geom
        query = "INSERT INTO body (id_hor,h_body,id_sort,geom) VALUES (" + str(id_hor) + "," + str(Hust) + ",4," + geom + ");"  
        curs.execute(query)
        # Скважины
        for j in range(-5, 5):
            # координаты скважины в БД
            query = "INSERT INTO drills (horiz,coord_system,type_drill,coord_x,coord_y,coord_z,name) VALUES ("
            query = query + str(id_hor) + ",1,1," + "%.0f,%.0f,%.0f" % ((X00 + D2 + R / 4), (Y00 + j * 10), Z) + ",'" + "%.0f/%.0f" % (Z, (j + 6)) + "') RETURNING id_drill_fld;"    
            #print query
            curs.execute(query)
            id_drill_fld = curs.fetchone()[0]
            # глубина скважины в параметры
            query = "INSERT INTO dril_pars (id_drill,id_par,val) VALUES ("
            query = query + str(id_drill_fld) + ",6," + "%.1f" % (Hust,) + ");"   
            #print query 
            curs.execute(query)
                
    conn.commit()  
    curs.close()
    conn.close() 

    t11 = time.time()
    self.msgWin.AppendText("Число вершин в контурах всех бровок = %f" % (Cnt) + "\n")
    print("Число вершин в контурах всех бровок = %f" % (Cnt))
    print("Время работы %f сек" % (t11 - t00))
    self.msgWin.AppendText("Время работы %f сек" % (t11 - t00) + "\n")
    self.SetStatusText("Готово", 2)

def CExplore(self):
    """ Заказ на просмотр элемента """
    sel_shape = self.canva._3dDisplay.selected_shape        # As shape
    #print sel_shape
    if sel_shape:
        print getPoints(sel_shape)
        for shapeInfo in self.canva.drawList:
            s1 = shapeInfo[2]   # As object
            if s1:
                if (s1.Shape().IsEqual(sel_shape)):
                    print ("Выбран " + str(shapeInfo))
                    self.SetStatusText("Результат на консоли", 2)
    else:
        self.SetStatusText("Выберите объект и повторите команду", 0)

def CEdit(self):
    """ Изменение координат объекта"""
    sel_shape = self.canva._3dDisplay.selected_shape
    if not sel_shape:
	self.SetStatusText("Выберите объект и повторите команду", 0)
	return
    pnts=getPoints(sel_shape)
    dlg = CoordsDlg(self, - 1, "Диалог изменения координат",pnts)#,int(self.body_cnt_h.Value))
    dlg.CenterOnScreen()
    dlg.ShowModal()
    if dlg.save:
	newpoints=dlg.ret()
	selObj = self.canva._3dDisplay.Context.SelectedInteractive()
	selColor = None
	if selObj.GetObject().HasColor():
	    selColor = self.canva._3dDisplay.Context.Color(selObj)
	self.canva._3dDisplay.Context.Erase(selObj)
	    
	indexInfo = None; 
	for i in range(len(self.canva.drawList)):
	    s1 = self.canva.drawList[i][2]
	    if s1:
		if (s1.Shape().IsEqual(sel_shape)):     # Только в классе Shape есть метод IsEqual()
		    indexInfo = i
                    break
        # get params sel object
	self.canva._3dDisplay.Context.Erase(selObj)           # Удалить старый
	plgn = BRepBuilderAPI_MakePolygon()             # Построить новый
	for pnt1 in newpoints:
	    plgn.Add(gp_Pnt(pnt1[0], pnt1[1], pnt1[2]))
	w = plgn.Wire()
	newShape = self.canva._3dDisplay.DisplayColoredShape(w,'YELLOW', False)        #,'WHITE'
	# Установить цвет, тип,толщину и др.
	if selColor:
	    self.canva._3dDisplay.Context.SetColor(newShape,selColor,0)
	if indexInfo <> None:
	    oldInfo = self.canva.drawList[indexInfo]
            oldInfo[2] = newShape.GetObject()
            oldInfo[5] = True
            self.canva.drawList[indexInfo] = oldInfo          # Обновить список
    dlg.Destroy()

#def CErase(self):
#    """ Заказ на удаление элемента """
#    self.canva.SetTogglesToFalse(event)
#    self.canva.MakeErase = True
#    self._refreshui()
#    self.SetStatusText("Укажите удаляемый элемент", 0)
        
def Coord_yes(self):
    """ Ввод координат из окна Point от кнопки или мыши """
    Z = float(self.canva.coordZ.GetValue())
    coordStr = self.canva.coord.GetValue()
    #print(coordStr)
    if self.canva.MakePLine:            
        # PolyLine
        drawP = False
        closeP = False
        if (len(self.canva.lstPnt) > 2): #Close or End
            if (coordStr.upper().find('C') <>- 1):   #Close
                #print('Close pline')
                drawP = True
                closeP = True
            if (not (coordStr.strip())):   #End
                #print('End pline')
                drawP = True
            #print('drawP=', drawP)
            if drawP:
                #if (self.canva._3dDisplay.Context.HasOpenedContext()):
                #    self.canva._3dDisplay.Context.CloseLocalContext()
                self.canva._3dDisplay.Context.Erase(self.canva.tmpEdge)
                self.canva.tmpEdge = None
                plgn = BRepBuilderAPI_MakePolygon()
                for pnt1 in self.canva.lstPnt:
                    plgn.Add(gp_Pnt(pnt1[0], pnt1[1], pnt1[2]))
                if closeP:
                    plgn.Close()
                w = plgn.Wire()
                self.canva._3dDisplay.DisplayColoredShape(w, 'YELLOW', False)        #,'WHITE'
                self.SetStatusText("Готово", 2)
                CancelOp(self)                 
                return

    coord1 = coordStr.split(',')
    lst1 = []
    for crd in coord1:
        try:
            lst1 = lst1 + [float(crd)]
        except Exception:
            self.SetStatusText("Ошибка в " + crd, 2)
            return
    if ((len(lst1) < 2) or (len(lst1) > 3)):
        self.SetStatusText("Ошибка в " + coordStr, 2)
        return
    elif len(lst1) == 2:
        lst1 = lst1 + [Z]
    self.canva.lstPnt = self.canva.lstPnt + [lst1]
    #print(self.canva.lstPnt)
    # Line
    if (self.canva.MakeLine) and (len(self.canva.lstPnt) > 1):
        #print self.canva.lstPnt
        pnt1 = self.canva.lstPnt[0]
        pnt2 = self.canva.lstPnt[1]
        edge = BRepBuilderAPI_MakeEdge(gp_Pnt(pnt1[0], pnt1[1], pnt1[2]),
            gp_Pnt(pnt2[0], pnt2[1], pnt2[2]))
        self.canva._3dDisplay.DisplayColoredShape(edge.Edge(), 'BLACK', False)        #
        self.SetStatusText("Готово", 2)
        CancelOp(self)
    # Временная линия    
    if (self.canva.MakePLine and (len(self.canva.lstPnt) > 1)):
        #if not (self.canva._3dDisplay.Context.HasOpenedContext()):
        #    self.canva._3dDisplay.Context.OpenLocalContext()    #False
            #self.canva.isLocalContext = True
        if self.canva.tmpEdge: 
            self.canva._3dDisplay.Context.Erase(self.canva.tmpEdge)
            self.canva.tmpEdge = None
        plgn = BRepBuilderAPI_MakePolygon()
        for pnt1 in self.canva.lstPnt:
            plgn.Add(gp_Pnt(pnt1[0], pnt1[1], pnt1[2]))
        w = plgn.Wire()
        self.canva.tmpEdge = self.canva._3dDisplay.DisplayColoredShape(w, 'ORANGE', False)        #,'WHITE'
                
def CancelOp(self):
    """ Отмена рисования элементов """
    #if (self.canva._3dDisplay.Context.HasOpenedContext()):
    #    self.canva._3dDisplay.Context.CloseLocalContext()
    #    self.canva.isLocalContext = False
    if self.canva.tmpEdge: 
        self.canva._3dDisplay.Context.Erase(self.canva.tmpEdge)
        self.canva.tmpEdge = None
    if self.canva.gumline_edge:
	self.canva._3dDisplay.Context.Erase(self.canva.gumline_edge)
	self.canva.gumline_edge=None
    self.canva.MakePLine = False
    self.canva.MakeLine = False
    self.canva.GumLine = False
    self.canva.lstPnt = []
    self.SetStatusText("Отмена", 2)
    self._refreshui()

def Refresh(self):
    self.msgWin.AppendText("Загрузка из базы данных\n")
    objLst = []
    for i in range(len(self.objList)):
        if self.chkObjs.IsChecked(i):
            objLst = objLst + [self.objList[i]]
    if objLst:
        lst = "Заданы объекты базы данных: "
        for obj in objLst:
            lst = lst + obj + ", "
        self.msgWin.AppendText(lst + "\n")
        #pass
    else:
        self.msgWin.AppendText("Не заданы объекты базы данных\n")
        return
    setHorIds = "("
    gorLst = []
    for i in range(len(self.horList)):
        if self.gorLst.IsChecked(i):
            gorLst = gorLst + [self.horIds[i]]
            setHorIds = setHorIds + str(self.horIds[i][0]) + ","
    setHorIds = setHorIds[: - 1] + ")"
    if gorLst:
        self.msgWin.AppendText("Заданы горизонты базы данных:" +  setHorIds + " -\n" +
                               str(gorLst) + "\n")
        #pass
    else:
        self.msgWin.AppendText("Не заданы горизонты базы данных\n")
        return
    # gorLst = [[id_hor, point, h_ledge, description], ...]
    # objLst = ["Бровки", "Тела", "Скважины", "Изолинии", "Отметки","Надписи", "БВР"]
    # Clear display
    self.canva._3dDisplay.EraseAll()
    self.canva.drawList = []

    if ("Бровки" in objLst):
        self.SetStatusText("Бровки", 2)
        conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
        curs = conn.cursor()
        query = "select id_edge,hor,edge_type,ST_AsEWKT(geom),point from edge,horizons "
        query = query + "where (id_hor in " + setHorIds + ") and (edge.hor=horizons.id_hor);"
        self.msgWin.AppendText("Query = " + query + "\n")
        curs.execute(query)
        rows = curs.fetchall()
        for rec in rows:
            #print(rec[0])
            id_edge = int(rec[0])
            id_hor = int(rec[1])
            edge_type = int(rec[2])
            coordsPLine = parsGeometry(str(rec[3]))
            point = float(rec[4])
            plgn = BRepBuilderAPI_MakePolygon()
            for pnt in coordsPLine:
                if len(pnt) < 3:
                    pnt = pnt + [point]
                #self.msgWin.AppendText(str(pnt) + ", ")
                plgn.Add(gp_Pnt(pnt[0], pnt[1], pnt[2]))
            w = plgn.Wire()
            s = self.canva._3dDisplay.DisplayColoredShape(w, 'BLUE', False)
            s1 = s.GetObject()
            self.canva.drawList = self.canva.drawList + [[0, id_edge, s1, id_hor, edge_type, False]]
        #print("Бровки=",self.canva.edgeList)
        self.SetStatusText("Готово!", 2)
        #pass

    if ("Тела" in objLst):
        self.SetStatusText("Тела", 2)
        conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
        curs = conn.cursor()
        query = "select id_body,body.id_hor,h_body,body.id_sort,ST_AsEWKT(geom),point,color,color_fill from body,horizons,sorts "
        query = query + "where (body.id_hor in " + setHorIds
        query = query + ") and (body.id_hor=horizons.id_hor) and (body.id_sort=sorts.id_sort);"
        self.msgWin.AppendText("Query = " + query + "\n")
        curs.execute(query)
        rows = curs.fetchall()
        for rec in rows:
            #print(rec[0])
            id_body = int(rec[0])
            id_hor = int(rec[1])
            h_body = int(rec[2])
            id_sort = int(rec[3])
            coordsPLine = parsGeometry(str(rec[4]))
            point = float(rec[5])
            color = int(rec[6])
            color_fill = int(rec[7])
            query = "select red,green,blue from color where id_color=" + str(color) + ";"
            curs.execute(query)
            clr = curs.fetchone()
            clrRed = clr[0]
            clrBlue = clr[1]
            clrGreen = clr[2]
                
            query = "select red,green,blue from color where id_color=" + str(color_fill) + ";"
            curs.execute(query)
            clr = curs.fetchone()
            clrFillRed = clr[0]
            clrFillBlue = clr[1]
            clrFillGreen = clr[2]
                
            plgn = BRepBuilderAPI_MakePolygon()
            for pnt in coordsPLine:
                if len(pnt) < 3:
                    pnt = pnt + [point]
                #print pnt
                plgn.Add(gp_Pnt(pnt[0], pnt[1], pnt[2]))
            plgn.Close()
            w = plgn.Wire()
            myFaceProfile = BRepBuilderAPI_MakeFace(w).Shape()
            aPrismVec = gp_Vec(0 , 0 , h_body);
            #print myFaceProfile, aPrismVec
            myBody = BRepPrimAPI_MakePrism(myFaceProfile, aPrismVec).Shape()
            #self.canva._3dDisplay.Context.SetMaterial(myBody,4)
            s = self.canva._3dDisplay.DisplayColoredShape(myBody, 'BLUE', False)
            s1 = s.GetObject()
            self.canva.drawList = self.canva.drawList + [[1, id_body, s1, id_hor, point, h_body, id_sort, color, color_fill, False]]
        #print("Тела=",self.canva.drawList)            
        self.SetStatusText("Готово!", 2)
        #pass

    if ("Скважины" in objLst):
        self.SetStatusText("Скважины", 2)
        conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
        curs = conn.cursor()
        query = "select id_drill_fld,horiz,coord_system,type_drill,coord_x,coord_y,coord_z,name from drills"
        query = query + " where (horiz in " + setHorIds + ");"
        self.msgWin.AppendText("Query = " + query + "\n")
        curs.execute(query)
        rows = curs.fetchall()
        for rec in rows:
            id_drill_fld, horiz, coord_system, type_drill, coord_x, coord_y, coord_z, name = rec
            # Прочитать глубину скважины из БД
            query = "SELECT val FROM dril_pars WHERE (id_par=6) and (id_drill=" + str(id_drill_fld) + ");"
            curs.execute(query)
            pars = curs.fetchone()
            if pars:
                dept = pars[0]
            else:
                dept = 16.0
            position = gp_Ax2(gp_Pnt(coord_x, coord_y, coord_z), gp_Dir(0, 0, - 1))
            skv = BRepPrim_Cylinder(position, 0.1, dept)
            skv = skv.Shell()
            s = self.canva._3dDisplay.DisplayColoredShape(skv, 'YELLOW', False)
            s1 = s.GetObject()
            self.canva.drawList = self.canva.drawList + [[2, id_drill_fld, s1, horiz, coord_system, type_drill, coord_x, coord_y, coord_z, dept, name, False]]
            #print [2,id_drill_fld,s1,horiz,coord_system,type_drill,coord_x,coord_y,coord_z,dept,name,False]
        self.SetStatusText("Готово!", 2)
        #pass

    if ("Изолинии" in objLst):
        #self.canva.drawList = []
        izoLst = (-10000, +10000)
        self.SetStatusText("Изолинии", 2)
        conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
        curs = conn.cursor()
        query = "select id_topo,heigth,coord_sys,ST_AsEWKT(geom) from topograph "
        query = query + "where (heigth>='" + str(izoLst[0]) + "')and(heigth<='" + str(izoLst[1]) + "')"
        self.msgWin.AppendText("Query = " + query + "\n")
        curs.execute(query)
        rows = curs.fetchall()
        for rec in rows:
            #print(rec[0])
            id_topo = int(rec[0])
            heigth = int(rec[1])
            coord_sys = int(rec[2])
            coordsPLine = parsGeometry(str(rec[3]))
            plgn = BRepBuilderAPI_MakePolygon()
            for pnt in coordsPLine:
                plgn.Add(gp_Pnt(pnt[0], pnt[1], heigth))
            w = plgn.Wire()
            s = self.canva._3dDisplay.DisplayColoredShape(w, 'GREEN', False)
            s1 = s.GetObject()
            self.canva.drawList = self.canva.drawList + [[3, id_topo, s1, heigth, coord_sys, False]]
        #print self.canva.drawList
        self.SetStatusText("Готово!", 2)
        #pass

    if ("Отметки" in objLst):
        pass

    if ("Надписи" in objLst):
        pass
    pass

def DemoPit(self):
        """ Прямое рисование элементов карьера без сохранения в СУБД 
        для нагрузочного тестирования"""
        self.SetStatusText("Бровки карьера", 2)
        n = 15
        X00 = 5000  # Center of pit
        Y00 = 5000
        Cnt = 0
        Hust = 15
        DLT_l = 5
        D2_D1 = 0.5
        R = 50
        D10 = 150
        Z0 = - 100
        t00 = time.time()
        for i in range(0, n):
            edgeUp = BRepBuilderAPI_MakePolygon()
            D1 = D10 + i * R
            Z = Z0 + (i * Hust)
            m = int(3.14 * D1 / DLT_l)
            D_Ugol = 6.28 / m
            for j in range(0, m):
                fi = j * D_Ugol
                X = X00 + D1 * cos(fi)
                Y = Y00 + D1 * sin(fi) * D2_D1
                edgeUp.Add(gp_Pnt(X, Y, Z))
                Cnt = Cnt + 1
            edgeUp.Close()
            self.canva._3dDisplay.DisplayColoredShape(edgeUp.Wire(), 'BLUE', False)
            edgeUp = BRepBuilderAPI_MakePolygon()
            D2 = D1 + R - Hust / 2
            for j in range(0, m):
                fi = j * D_Ugol
                X = X00 + D2 * cos(fi)
                Y = Y00 + D2 * sin(fi) * D2_D1
                edgeUp.Add(gp_Pnt(X, Y, Z))
                Cnt = Cnt + 1
            edgeUp.Close()
            self.canva._3dDisplay.DisplayColoredShape(edgeUp.Wire(), 'BLUE', False)
            self.canva._3dDisplay.DisplayMessage(gp_Pnt(X00 + D2 + 2, Y00, Z), str(Z), False)
        t11 = time.time()        
        print("Число вершин в контурах всех бровок = %f" % (Cnt))
        print("Время работы %f сек" % (t11 - t00))
        self.msgWin.AppendText("Число вершин в контурах всех бровок = %f" % (Cnt) + "\n")
        self.msgWin.AppendText("Время работы %f сек" % (t11 - t00) + "\n")
        self.SetStatusText("Бровки готовы", 2)
        #self.msgWin.AppendText(  + "\n")
        
def LoadDB(self):
        """ Загрузка элементов из базы данных PostGIS """
        dlg = LoadDlg(self, - 1, "Диалог загрузки БД")
        dlg.CenterOnScreen()
        dlg.ShowModal()
        resDict = dlg.result()
        # {'izoLst': (250.0, 260.0), 'objList': [0, 1, 2, 3], 'horIds': [1, 3]}
        # objList: 0 - "Бровки", 1 - "Тела", 2 - "Скважины", 3 - "Изолинии"]
        dlg.Destroy()
        #print resDict
        if len(resDict) == 0:
            return
        horIds = resDict['horIds']      # Список ключей горизонтов
        setHorIds = "("
        for h in horIds:
            setHorIds = setHorIds + str(h) + ","
        setHorIds = setHorIds[: - 1] + ")"
        objList = resDict['objList']    # Список типов объектов из БД
        izoLst = resDict['izoLst']     # Диапазон отметок изолиний
        # Clear display
        self.canva._3dDisplay.EraseAll()
        self.canva.drawList = []

        if (0 in objList):      # Бровки
            self.SetStatusText("Бровки", 2)
            conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
            curs = conn.cursor()
            query = "select id_edge,hor,edge_type,ST_AsEWKT(geom),point from edge,horizons "
            query = query + "where (id_hor in " + setHorIds + ") and (edge.hor=horizons.id_hor);"
            curs.execute(query)
            rows = curs.fetchall()
            for rec in rows:
                #print(rec[0])
                id_edge = int(rec[0])
                id_hor = int(rec[1])
                edge_type = int(rec[2])
                coordsPLine = parsGeometry(str(rec[3]))
                point = float(rec[4])
                plgn = BRepBuilderAPI_MakePolygon()
                for pnt in coordsPLine:
                    if len(pnt) < 3:
                        pnt = pnt + [point]
                    #print pnt
                    plgn.Add(gp_Pnt(pnt[0], pnt[1], pnt[2]))
                w = plgn.Wire()
                s = self.canva._3dDisplay.DisplayColoredShape(w, 'BLUE', False)
                s1 = s.GetObject()
                self.canva.drawList = self.canva.drawList + [[0, id_edge, s1, id_hor, edge_type, False]]
            #print("Бровки=",self.canva.edgeList)
            self.SetStatusText("Готово!", 2)
            pass
        
        if (1 in objList):      # Тела
            self.SetStatusText("Тела", 2)
            conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
            curs = conn.cursor()
            query = "select id_body,body.id_hor,h_body,body.id_sort,ST_AsEWKT(geom),point,color,color_fill from body,horizons,sorts "
            query = query + "where (body.id_hor in " + setHorIds
            query = query + ") and (body.id_hor=horizons.id_hor) and (body.id_sort=sorts.id_sort);"
            curs.execute(query)
            rows = curs.fetchall()
            for rec in rows:
                #print(rec[0])
                id_body = int(rec[0])
                id_hor = int(rec[1])
                h_body = int(rec[2])
                id_sort = int(rec[3])
                coordsPLine = parsGeometry(str(rec[4]))
                point = float(rec[5])
                color = int(rec[6])
                color_fill = int(rec[7])
                query = "select red,green,blue from color where id_color=" + str(color) + ";"
                curs.execute(query)
                clr = curs.fetchone()
                clrRed = clr[0]
                clrBlue = clr[1]
                clrGreen = clr[2]
                
                query = "select red,green,blue from color where id_color=" + str(color_fill) + ";"
                curs.execute(query)
                clr = curs.fetchone()
                clrFillRed = clr[0]
                clrFillBlue = clr[1]
                clrFillGreen = clr[2]
                
                plgn = BRepBuilderAPI_MakePolygon()
                for pnt in coordsPLine:
                    if len(pnt) < 3:
                        pnt = pnt + [point]
                    #print pnt
                    plgn.Add(gp_Pnt(pnt[0], pnt[1], pnt[2]))
                plgn.Close()
                w = plgn.Wire()
                myFaceProfile = BRepBuilderAPI_MakeFace(w).Shape()
                aPrismVec = gp_Vec(0 , 0 , h_body);
                #print myFaceProfile, aPrismVec
                myBody = BRepPrimAPI_MakePrism(myFaceProfile, aPrismVec).Shape()
                #self.canva._3dDisplay.Context.SetMaterial(myBody,4)
                s = self.canva._3dDisplay.DisplayColoredShape(myBody, 'BLUE', False)
                s1 = s.GetObject()
                self.canva.drawList = self.canva.drawList + [[1, id_body, s1, id_hor, point, h_body, id_sort, color, color_fill, False]]
            #print("Тела=",self.canva.drawList)            
            self.SetStatusText("Готово!", 2)
            pass
        
        if (2 in objList):      # Скважины
            self.SetStatusText("Скважины", 2)
            conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
            curs = conn.cursor()
            query = "select id_drill_fld,horiz,coord_system,type_drill,coord_x,coord_y,coord_z,name from drills"
            query = query + " where (horiz in " + setHorIds + ");"
            curs.execute(query)
            rows = curs.fetchall()
            for rec in rows:
                id_drill_fld, horiz, coord_system, type_drill, coord_x, coord_y, coord_z, name = rec
                # Прочитать глубину скважины из БД
                query = "SELECT val FROM dril_pars WHERE (id_par=6) and (id_drill=" + str(id_drill_fld) + ");"
                curs.execute(query)
                pars = curs.fetchone()
                if pars:
                    dept = pars[0]
                else:
                    dept = 16.0
                position = gp_Ax2(gp_Pnt(coord_x, coord_y, coord_z), gp_Dir(0, 0, - 1))
                skv = BRepPrim_Cylinder(position, 0.1, dept)
                skv = skv.Shell()
                s = self.canva._3dDisplay.DisplayColoredShape(skv, 'YELLOW', False)
                s1 = s.GetObject()
                self.canva.drawList = self.canva.drawList + [[2, id_drill_fld, s1, horiz, coord_system, type_drill, coord_x, coord_y, coord_z, dept, name, False]]
                #print [2,id_drill_fld,s1,horiz,coord_system,type_drill,coord_x,coord_y,coord_z,dept,name,False]
            self.SetStatusText("Готово!", 2)
            pass        
        
        if (3 in objList):      # Изолинии
            #self.canva.drawList = []
          
            self.SetStatusText("Изолинии", 2)
            conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
            curs = conn.cursor()
            curs.execute("select id_topo,heigth,coord_sys,ST_AsEWKT(geom) from topograph " + 
                         "where (heigth>='" + str(izoLst[0]) + "')and(heigth<='" + str(izoLst[1]) + "')")
            rows = curs.fetchall()
            for rec in rows:
                #print(rec[0])
                id_topo = int(rec[0])
                heigth = int(rec[1])
                coord_sys = int(rec[2])
                coordsPLine = parsGeometry(str(rec[3]))
                plgn = BRepBuilderAPI_MakePolygon()
                for pnt in coordsPLine:
                    plgn.Add(gp_Pnt(pnt[0], pnt[1], heigth))
                w = plgn.Wire()
                s = self.canva._3dDisplay.DisplayColoredShape(w, 'GREEN', False)
                s1 = s.GetObject()
                self.canva.drawList = self.canva.drawList + [[3, id_topo, s1, heigth, coord_sys, False]]
            #print self.canva.drawList
            self.SetStatusText("Готово!", 2)
            pass
        
def SaveDB(self):
        """ Сохранить изменения в БД """
        self.SetStatusText("Сохранение в БД", 2)
        conn = psycopg2.connect("dbname="+POSTGR_DBN+" user="+POSTGR_USR)
        curs = conn.cursor()
        for indexInfo in range(len(self.canva.drawList)):
            element = self.canva.drawList[indexInfo]
            if element[ - 1]:             # Был изменен
                #print(element)
                if element[0] == 0:     # Бровка                    
                    id = element[1]
                    s1 = element[2]     # Объект
                    if s1 == None:      # Удалять из БД
                        query = "DELETE FROM edge WHERE id_edge=" + str(id) + ";"  
                        #print query
                        curs.execute(query)
                    else:               # Модифицировать в БД    
                        pnts = getPoints(s1.Shape())
                        geom = makeLINESTRING(pnts)
                        query = "UPDATE edge SET geom=" + geom + " WHERE id_edge=" + str(id) + ";"  
                        #print query
                        curs.execute(query)
                    element[ - 1] = False # Снять флаг модификации
                    self.canva.drawList[indexInfo] = element
        conn.commit()  
        curs.close()
        conn.close() 
        self.SetStatusText("Готово!", 2)
        #print(self.canva.drawList)
        pass
    
def noise():
    MAXNOISE = 0.00
    return MAXNOISE * (random() - 0.5)
        
def Lidar(self):
        """ Загрузка элементов из .las файла """
        dltX = 2.0; dltY = 2.0;     # шаг сетки чертежа и хранения точек
        dltD = sqrt(dltX*dltX+dltY*dltY)    # Допуск на расстояние до бровки
        dltp = 1.0                  # длина штриха на рисунке
        KUKL = 1.5                  # |a| + |b| -- Наклон поверхности aX+bY=c 

        #HdZ  = 1.0
        #HddZ = 1.0
        
        def log(x,y):       ## Точка в области журнализации для отладочных выдач в журнал
            DLT_ij = 5
            WX0 = 4964; WX1 = 5040;
            WY0 = 4880; WY1 = 4920;
            #return (iX in range(nX/2-DLT_ij,nX/2+DLT_ij)) or (iY in range(nY/2-DLT_ij,nY/2+DLT_ij))
            return (WX0<x<WX1) and (WY0<y<WX1)
        
        
        self.SetStatusText("Загрузка LiDAR снимка", 2)
        if not hasattr(self, "lasdir"):
            self.lasdir = "../../LibLas_Python/Las/"
        dlg = wx.FileDialog(self, "Задание имени файла", self.lasdir, "",
                         "Las Files (*.las)|*.las|All Files (*.*)|*.*",
                         wx.OPEN)
        if dlg.ShowModal() <> wx.ID_OK:
            dlg.Destroy()
            self.SetStatusText("LiDAR не задан файл", 2)
            return False
        
        laspathname = dlg.GetPath()
        self.lasdir = os.path.dirname(laspathname)
        dlg.Destroy()
        
        fLog = open(laspathname+'.log', 'w',0)		# Создание файла журнала
        
        fLas = file.File(laspathname, mode='r')		# Открыли файл со снимком LIDAR
        h = fLas.header					# Прочли заголовок снимка и разобрали по атрибутам для журнала
        #print "h.major_version, h.minor_version = ", [h.major_version, h.minor_version]
        fLog.write("h.major_version, h.minor_version = "+ str([h.major_version, h.minor_version])+"\n")
        #print "h.dataformat_id = ", [h.dataformat_id]        
        fLog.write("h.dataformat_id = "+ str([h.dataformat_id])+"\n")        
        #print "h.min = ", [h.min]
        fLog.write("h.min = "+ str([h.min])+"\n")   
        #print "h.max = ", [h.max]
        fLog.write("h.max = "+ str([h.max])+"\n") 
        #print "h.scale = ", [h.scale]
        fLog.write("h.scale = "+ str([h.scale])+"\n") 
        #print "h.offset = ", [h.offset]
        fLog.write("h.offset = "+ str([h.offset])+"\n") 
        #print "h.project_id = ", [h.project_id]
        fLog.write("h.project_id = "+ str([h.project_id])+"\n")
        #print "h.guid = ", [h.guid]
        fLog.write("h.guid = "+ str([h.guid])+"\n")
        #print "h.point_records_count = ", h.point_records_count
        fLog.write("h.point_records_count = "+ str(h.point_records_count)+"\n")
        #print " =============== "
        fLog.write(" =============== \n")
        nPnt = h.point_records_count	# Число точек в снимке
        
        if (nPnt == 0):
            fLas.close()
            self.SetStatusText("LiDAR файл пустой", 2)
            return False
        minX = h.min[0]; minY = h.min[1];	# Пределы для координат снимка
        maxX = h.max[0]; maxY = h.max[1];
        nX = int((maxX - minX) / dltX)		# Число клеток в матрице
        nY = int((maxY - minY) / dltY)
        #print "nX = ", nX, " nY = ", nY
        XYZ = []                        # Матрица пустых клеток-областей с точками
        for iX in range(nX + 2):        # размер матрицы по Х с запасом клеток по краям области
            YZ = []			# строка матрицы
            for iY in range(nY + 2):    # размер матрицы по У с запасом клеток по краям области
                YZ.append([])		# пустая клетка в столбец
            XYZ.append(YZ)		# столбец в матрицу
            #self.SetStatusText(""+str(int(iX/nX*100))+"%", 2)
        sTime = time.time()    
        #print 'Чтение точек Las'
        shapes = []; iPnt = 0
        for p in fLas:      # по точкам из файла-снимка в клетки матрицы
            iPnt = iPnt + 1
            iX = int((p.x - minX - h.offset[0]) / dltX)             # номер клетки по Х
            iY = int((p.y - minY - h.offset[1]) / dltY)             # номер клетки по У
            #print "iX = ",iX, " iY = ",iY, p.x,minX,dltX,p.y,minY,dltY
            ((XYZ[iX])[iY]).append([p.x - h.offset[0], p.y - h.offset[1], p.z - h.offset[2] + noise()])       #  смещенные точки ???
            #if (int(iPnt/1000)*1000 == iPnt):
            #    self.SetStatusText(""+str(int(iPnt/nPnt*100))+"%", 2)
        #print "Прочли за ", str(time.time() - sTime), " сек ", iPnt, " точек."
        # XYZ - прямоугольный массив клеток со смещенными точками. Клетка может быть пустой 
        # Поиск средних для клетки
        sXYZ = []
        sTime = time.time() 
        #print "Поиск средних для клетки "
        for iX in range(nX + 2):
            sYZ = []
            for iY in range(nY + 2):
                cloud = (XYZ[iX])[iY]           # Содержимое клетки
                if cloud:
                    nc = 0; Zc = 0.0; Xc = 0.0; Yc = 0.0
                    for p in cloud:
                        nc = nc + 1
                        Xc = Xc + p[0]
                        Yc = Yc + p[1]
                        Zc = Zc + p[2]
                    Xc = Xc / nc; Yc = Yc / nc; Zc = Zc / nc; 
                    sYZ.append([Xc, Yc, Zc])    # Средняя точка клетки
                else:
                    sYZ.append([])
            sXYZ.append(sYZ)
        print "Нашли за ", str(time.time() - sTime), " сек"
        # sXYZ - массив средних для клеток
        # Первые разности          
        sTime = time.time() 
        HdZ = sqrt(dltX*dltX+dltY*dltY)*0.9     # Порог контраста dltX = 2.0; dltY = 2.0;
        #print "Первые разности"  
        dXYZ = []
        for iX in range(nX + 2):
            dYZ = []
            for iY in range(nY + 2):
                pnt = (sXYZ[iX])[iY];
                if pnt:
                    Xc,Yc,Zc = pnt;
                    ns = 0; dZ = 0.0
                    for sX in [ - 1, 0, + 1]:
                        if ((iX + sX) >= 0) and ((iX + sX) <= nX):
                            for sY in [ - 1, 0, + 1]:
                                if ((iY + sY) >= 0) and ((iY + sY) <= nY):
                                    sXY = ((XYZ[iX + sX])[iY + sY])[0]
                                    if not ((sX == 0) and (sY == 0)) and sXY:
                                        ns = ns + 1
                                        dZ = dZ + abs(sXY[2] - Zc)
                    if ns > 0:
                        dZ = dZ / ns    # Средняя первая разность
                        if dZ > HdZ:    # Порог контраста dltX = 2.0; dltY = 2.0;
                            dZ = 1.0
                        else:
                            dZ = 0.0
                        dZ = [dZ, ]      
                    else: 
                        dZ = []
                else:
                    dZ = []               
                dYZ.append(dZ)
            dXYZ.append(dYZ)
            
        #print "Нашли за ", str(time.time() - sTime), " сек"
        
        # Вторые разности
        sTime = time.time() 
        #print "Вторые разности"  
        ddXYZ = []
        for iX in range(nX + 2):
            ddYZ = []
            for iY in range(nY + 2):
                dZ = (dXYZ[iX])[iY]                                 # [dZ]
                if dZ:
                    ns = 0; ddZ = 0.0
                    for sX in [ - 1, 0, + 1]:
                        if (((iX + sX) >= 0) and ((iX + sX) <= nX)):
                            for sY in [ - 1, 0, + 1]:
                                if (((iY + sY) >= 0) and ((iY + sY) <= nY)):
                                    #print ((XYZ[iX+sX])[iY+sY])
                                    dXY = ((dXYZ[iX + sX])[iY + sY])      # [Первая разность соседа]
                                    if not((sX == 0) and (sY == 0)) and dXY:
                                        ns = ns + 1
                                        if type(dXY).__name__ <> 'list':
                                            print 'Error ddZ: ',dXY, dZ, ((XYZ[iX + sX])[iY + sY])
                                        ddZ = ddZ + abs(dXY[0] - dZ[0])
                    if ns > 0:
                        #ddZ = ddZ / ns       # Средняя разность
                        if ddZ > 0.5:
                            ddZ = 1.0
                        else:
                            ddZ = 0.0
                        ddZ = [ddZ, ]        # [Средняя вторая разность]
                    else: 
                        ddZ = []
                else:
                    ddZ = []               
                ddYZ.append(ddZ)
            ddXYZ.append(ddYZ)
                
        #print "Нашли за ", str(time.time() - sTime), " сек"
        
        # Поверхности для клетки        Z = b0 + b1*X + b2 * Y
        sTime = time.time() 
        #print "Поверхности для клетки"  
        gistAB = []
        for i in range(51): 
            gistAB.append(0)
        povXYZ = []
        for iX in range(nX + 2):
            povYZ = []
            for iY in range(nY + 2):
                cloud = (XYZ[iX])[iY]
                if cloud:
                    Xc, Yc, Zc = sXYZ[iX][iY]
                    pov = getMNK(cloud, offset=[Xc, Yc, Zc]) #array ([[b0],[b1],[b2]])
                    povYZ.append(pov)
                    if pov:
                        nGist = int((abs(pov[1])+abs(pov[2]))*10)
                        if (nGist>50): nGist = 50
                        gistAB[nGist] = gistAB[nGist]+1                    
                else:
                    povYZ.append([])
            povXYZ.append(povYZ)
        # print "gistAB= ", gistAB       
        #print "Нашли поверхности в клетках за ", str(time.time() - sTime), " сек"
        # Выборочная печать клеток
        #i = 0
        #for iX in range(nX+2):
        #    for iY in range(nY+2):
        #        i = i + 1
        #        if fmod(i,121)==0:
        #            print iX,iY,sXYZ[iX][iY], povXYZ[iX][iY], XYZ[iX][iY]
        
        # Рисование клеток	НЕ ВЫПОЛНЯЕТСЯ См. условие == False
        if (False):
            #print 'Рисование клеток'    
            fLog.write('\nРисование клеток\n\n')
            sTime = time.time() 
            plosk = []; otkos = []
            for iX in range(nX + 2):
                for iY in range(nY + 2):
                    pnt = ((sXYZ[iX])[iY]);
                    pov = ((povXYZ[iX])[iY]); 
                    if pov:
                        plgn = BRepBuilderAPI_MakePolygon()
                        dltX = 2.0; dltY = 2.0;
                        x,y,z = pnt
                        plgn.Add(gp_Pnt(x - dltX*0.4 , y - dltY*0.4 , z))
                        plgn.Add(gp_Pnt(x + dltX*0.4 , y + dltY*0.4 , z))
                        plgn.Add(gp_Pnt(x - dltX*0.4 , y + dltY*0.4 , z))
                        plgn.Add(gp_Pnt(x + dltX*0.4 , y - dltY*0.4 , z))
                        plgn.Add(gp_Pnt(x - dltX*0.4 , y - dltY*0.4 , z))
                        plgn.Add(gp_Pnt(x - dltX*0.4 , y + dltY*0.4 , z))
                        plgn.Add(gp_Pnt(x + dltX*0.4 , y + dltY*0.4 , z))
                        plgn.Add(gp_Pnt(x + dltX*0.4 , y - dltY*0.4 , z))
                        w = plgn.Wire()
                        if abs(pov[1])+abs(pov[2])>KUKL:                # на уклоне
                            otkos.append(w)
                        else:
                            plosk.append(w)
            self.canva._3dDisplay.DisplayColoredShape(plosk, 'WHITE', False)                             
            self.canva._3dDisplay.DisplayColoredShape(otkos, 'GREEN', False)         
        
        
            #print "Рисование клеток за ", str(time.time() - sTime), " сек"
        
        #print 'Поиск граничных точек'    
        fLog.write('\nПоиск граничных точек\n\n')
        sTime = time.time() 
        HdZ = 0.5; HddZ = 0.5;      #HdZ
        #shapes = []
        granXYZ = []		# матрица с точками на границах
        iPnt = 0
        for iX in range(nX + 2):
            granYZ = []
            for iY in range(nY + 2):
                pnt = ((sXYZ[iX])[iY]); dZ = ((dXYZ[iX])[iY]); ddZ = ((ddXYZ[iX])[iY])
                #print pnt, dZ, ddZ
                if pnt and dZ and ddZ and (dZ[0] < HdZ) and (ddZ[0] > HddZ):     # По площадке у бровки. Искать здесь
                    # Найти плоскости с минимальным и максимальным уклоном в окресности точки pnt = sXYZ[iX])[iY]
                    if log(pnt[0],pnt[1]):
                        fLog.write("iX="+str(iX)+" iY="+str(iY)+" pnt="+str(pnt)+" dZ="+str(dZ)+" ddZ="+str(ddZ)+"\n")
                    horRgn = uklRgn = []                                # индексы областей площадки и уклона
                    for i in (-2,-1, 0, 1, 2):                          #        7 8 9
                        for j in (-2, -1, 0, 1, 2):                     #        4 x 6
                            rgn = XYZ[iX + i][iY + j]                   #        1 2 3
                            pov = povXYZ[iX + i][iY + j]                # [b0,b1,b2]
                            if log(pnt[0],pnt[1]):
                                fLog.write("i="+str(i)+" j="+str(j)+" rgn="+str(rgn)+" pov="+str(pov)+"\n")
                            if rgn and pov:         # and not((i==0) and (j==0)): 
                                if abs(pov[1])+abs(pov[2])>KUKL:                # на уклоне
                                    if not(uklRgn):                             # Первая область на уклоне
                                        uklRgn = [iX + i,iY + j]
                                    else:
                                        p1 = (sXYZ[iX+i])[iY+j]                 # Новая середина
                                        p2 = (sXYZ[uklRgn[0]])[uklRgn[1]]       # Старая середина
                                        if distance2d(pnt,p1) < distance2d(pnt,p2):
                                            uklRgn = [iX + i,iY + j]            # ближе
                                else:                                           # на площадке
                                    if not(horRgn):
                                        horRgn = [iX + i,iY + j]
                                    else:
                                        p1 = (sXYZ[iX+i])[iY+j]                 # Новая
                                        p2 = (sXYZ[horRgn[0]])[horRgn[1]]       # Старая
                                        if distance2d(pnt,p1) < distance2d(pnt,p2):
                                            horRgn = [iX + i,iY + j]
                    if log(pnt[0],pnt[1]):
                        fLog.write("uklRgn="+str(uklRgn)+" horRgn="+str(horRgn)+"\n")
                            
                    # Найти линию пересечения плоскостей uklRgn и horRgn                  
                    # Найти проекцию точки pnt на пересечение плоских граней
                    if uklRgn:
                        xc,yc,zc = (sXYZ[uklRgn[0]])[uklRgn[1]] 
                    else:
                        xc,yc,zc = pnt
                    if horRgn:
                        xp,yp,zp = (sXYZ[horRgn[0]])[horRgn[1]]
                    else:
                        xp,yp,zp = pnt
                    try:
                        b0,b1,b2 = (povXYZ[uklRgn[0]])[uklRgn[1]]           ## z = b0 + b1*(x-xc) + b2*(y-yc)   xc,yc,zc уклон
                        p0,p1,p2 = (povXYZ[horRgn[0]])[horRgn[1]]           ## z = p0 + p1*(x-xp) + p2*(y-yp)   xp,yp,zp площадка
                        A1 = b1; B1 = b2; C1 = -1.0; D1 = b0-b1*xc-b2*yc    ## A1*x + B1*y + C1*z + D1 = 0 - уклон
                        A2 = p1; B2 = p2; C2 = -1.0; D2 = p0-p1*xc-p2*yc    ## A2*x + B2*y + C2*z + D2 = 0 - площадка
                        if (abs(b1) < 0.000001): 
                            K = 0.0
                        else:
                            K = b2/b1
                        x = (B1*K*xc-B1*yc-D1-(C1/C2)*B2*xc+(C1/C2)*B2*yc+(C1/C2)*D2) / (A1+B1*K-(C1/C2)*A2-(C1/C2)*B2*K)
                        y = K*(x - xc) + yc
                        z = (-1.0/C2)*(A2*x+B2*y+D2)
                        p = [x,y,z]
                        if log(pnt[0],pnt[1]):                            
                            fLog.write("b0="+str(b0)+" b1="+str(b1)+" b2="+str(b2)+"\n")
                            fLog.write("p0="+str(p0)+" p1="+str(p1)+" p2="+str(p2)+"\n")
                            fLog.write("xc="+str(xc)+" yc="+str(yc)+" zc="+str(zc)+"\n")
                            fLog.write("xp="+str(xp)+" yp="+str(yp)+" zp="+str(zp)+"\n")
                            fLog.write("A1="+str(A1)+" B1="+str(B1)+" D1="+str(D1)+"\n")
                            fLog.write("A2="+str(A1)+" B2="+str(B2)+" D2="+str(D2)+"\n")
                            fLog.write("K="+str(K)+" x="+str(x)+" y="+str(y)+" z="+str(z)+"\n")

                        dz = zp - zc
                        d = dz/(b1*b1+b2*b2)
                        dx = d*b1; dy = d*b2
                        p_1 = [xc+dx,yc+dy,zc+dz]
                    except:
                        p = pnt
                    if (distance3d(pnt,p)>distance3d(pnt,p_1)):
                        p = p_1
                    # Сохранить граничную точку
                    granYZ.append(p)
                    if log(pnt[0],pnt[1]):
                        fLog.write("p="+str(p)+"\n")
                    # Вариант: построить триангуляцию окрестности по фактическим точкам
                    #    построить профиль вдоль линии градиента откоса
                    #    найти на профиле точки перелома
                    #    по соотношению отметок откоса и площадки идентифицировать нижнюю и верхнюю бровки
                    #    по шаблонам распознать валик и осыпь, найти искомые точки и сохранить
                    #
                    #
        #            try:
        #                Xc = float(pnt[0])
        #                Yc = float(pnt[1])
        #                Zc = float(pnt[2])
        #                edge = BRepBuilderAPI_MakeEdge(gp_Pnt(Xc, Yc, Zc), gp_Pnt(Xc-dltp, Yc-dltp, Zc-dltp))
        #                shapes.append(edge.Edge())
        #                iPnt = iPnt + 1
        #            except:
        #                print '*********************'
        #                pass
                else:
                    granYZ.append([])
            granXYZ.append(granYZ)
            
            #self.SetStatusText(""+str(int(iX/nX*100))+"%", 2)
                #self.canva._3dDisplay.DisplayColoredShape(edge.Edge(), 'BLUE', False)
        #self.canva._3dDisplay.DisplayColoredShape(shapes, 'RED', False)
        #fLog.write("granXYZ="+str(granXYZ)+"\n")
        #print "Нашли границы за ", str(time.time() - sTime), " сек " , iPnt, " точек"

        hors = [[[X00,Y00,Z00],0]]              # [[центр карьера], радиус верхней бровки]
        for i in range(0, n):                   # По уступам горизонтов
            rDn = R10 + i * R                   # Радиус нижней бровки
            zDn = Z00 + (i * Hust)              # Отметка нижней бровки
            hors.append([[X00,Y00,zDn], rDn])   # Нижняя бровка
            rUp = rDn + Hust/tan(Ugl)           # Радиус верхней бровки
            zUp = zDn + Hust                    # Отметка верхней бровки
            hors.append([[X00,Y00,zUp], rUp])   # Верхняя бровка

        
        #print 'Рисование бровок'    
        sTime = time.time() 
        edges = []		# Список фрагментов бровки для отрисовки
        # Сборка бровок из точек на границах
        while True: # Найти некоторую точку - якорь
            line = []
            for iX in range(1, nX + 1):            
                for iY in range(1, nY + 1):
                    gpnt = granXYZ[iX][iY]              # [iX,iY,[px,py,pz]]
                    if gpnt:
                        line.append([iX,iY,gpnt])       # Координаты точки [iX,iY,[px,py,pz]]
                        #line.append((iX, iY,))         # Номера клетки в матрице
                        granXYZ[iX][iY] = []            # erase cell
                        break                           # Нашли якорь
                if line:
                    break
            if not line:                                # НЕ Нашли якорь
                break
            # Продолжить вперед от якорного фрагмента
            while True:
                yesPnt = False
                curX, curY, pnt = line[ - 1]    # -1 последняя  # Последовательность обхода точек окрестности точки pnt
                for i in (-1, 0, 1):                            #        7 8 9
                    for j in (-1, 0, 1):                        #        4 x 6
                        gpnt = granXYZ[curX + i][curY + j]      #        1 2 3
                        if gpnt:                          
                            line.append([curX + i,curY + j,gpnt])      	# продлили линию
                            granXYZ[curX + i][curY + j] = []        	# стерли использованную точку
                            yesPnt = True
                            break
                    if yesPnt: break
                if not yesPnt: break            
            
            # Продолжить назад от якорного фрагмента
            while True:
                yesPnt = False
                curX, curY, pnt = line[0]    # 0 первая точка фрагмента
                for i in (-1, 0, 1):
                    for j in (-1, 0, 1):
                        gpnt = granXYZ[curX + i][curY + j]
                        if gpnt: 
                            line.insert(0, [curX + i,curY + j,gpnt])   	# продлили линию
                            granXYZ[curX + i][curY + j] = []        	# стерли использованную точку
                            yesPnt = True
                    if yesPnt: break
                if not yesPnt: break 
            edges.append(line)		# Добавить фрагмент бровки в список на отрисовку
        fLog.write("\n\nedges\n\n")
        shapes = []			# Список форм для отрисовки
        cntPnt = 0; sumErrP = 0.0; sumErrZ = 0.0; sumErr = 0.0        # Расчет погрешностей в плане и по высоте
        for line in edges:
            fLog.write("line="+str(line)+"\n")
            if len(line) > 2:
                plgn = BRepBuilderAPI_MakePolygon()		# Пустой полигон для рисования бровки
                for pnt in line:
                    #iX, iY = pnt
                    x, y, z = pnt[2]       # (sXYZ[iX])[iY]
                    plgn.Add(gp_Pnt(x, y, z))			# Добавили точку в полигон
                    xC = x-X00; yC = y-Y00; rxy = sqrt(pow((x - X00), 2) + pow(((y-Y00)/D2_D1), 2))
                    errP = None; errZ = None
                    for hor in hors:
                        xc1,yc1,zc1 = hor[0]
                        rHor = hor[1]
                        if abs(rHor - rxy) < 3:            # Нашли бровку эталона
                            xHor = xC*(rHor/rxy); yHor = yC*(rHor/rxy); zHor = zc1
                            errP = sqrt(pow((xC - xHor), 2) + pow((yC-yHor), 2))     # Найти погрешность в плане      
                            err = sqrt(pow((xC - xHor), 2) + pow((yC-yHor), 2) + pow((z-zc1), 2))  # Найти погрешность общую
                            break
                    if errP <> None:
                        sumErr = sumErr + err
                        sumErrP = sumErrP + errP
                        sumErrZ = sumErrZ + abs(z - zc1)
                        cntPnt = cntPnt + 1
                w = plgn.Wire()		# Преобразование полигона в каркас
                shapes.append(w)	# Добавили каркас в список форм для отрисовки
        self.canva._3dDisplay.DisplayColoredShape(shapes, 'BLUE', False)     # Рисование форм на экране синим цветом  
        
        sumErrP = sumErrP/cntPnt 
        sumErrZ = sumErrZ/cntPnt   
        sumErr = sumErr/cntPnt   
        print "Средняя погрешность в плане = ", sumErrP, " по высоте = ", sumErrZ, " общая = ", sumErr
        print "Нарисовали за ", str(time.time() - sTime), " сек " , cntPnt, " точек"
        self.msgWin.AppendText("Средняя погрешность в плане = " + str(sumErrP) +
                               " по высоте = " + str(sumErrZ) +
                               " общая = " + str(sumErr)  + "\n")
        self.msgWin.AppendText("Нарисовали за " + str(time.time() - sTime) + " сек " + str(cntPnt) + " точек"  + "\n")
        self.SetStatusText("Готово!", 2)
        #print 'Finish Las'
        pass
        fLog.write("Нарисовали бровки за "+str(time.time() - sTime)+ "сек. Число точек = "+str(iPnt)+" \n")
        fLog.close()
    
        # Закрашивание бортов и площадок 
        
    
def Etalon(self):
        # Рисование эталона
        #print "Построение эталона карьера"
        startTime = time.time()

        Cnt = 0        
        for i in range(0, n):               # По числу уступов горизонтов
            rDn = R10 + i * R               # Радиус  нижней бровки
            zDn = Z00 + (i * Hust)          # Отметка нижней бровки
            rUp = rDn + Hust/tan(Ugl)       # Радиус  верхней бровки
            zUp = zDn + Hust                # Отметка верхней бровки
            m   = int(6.28 * rDn / DLT_l)   # Число точек на бровках
            D_Ugol = 6.28 / m               # Приращение угла поворота луча
            edgeDn = BRepBuilderAPI_MakePolygon()
            for j in range(0, m):
                fi = j * D_Ugol
                X = X00 + rDn * cos(fi)
                Y = Y00 + rDn * sin(fi) * D2_D1
                edgeDn.Add(gp_Pnt(X, Y, zDn))
                Cnt = Cnt + 1
            edgeDn.Close()
            self.canva._3dDisplay.DisplayColoredShape(edgeDn.Wire(), 'GREEN', False)
            
            edgeUp = BRepBuilderAPI_MakePolygon()
            for j in range(0, m):
                fi = j * D_Ugol
                X = X00 + rUp * cos(fi)
                Y = Y00 + rUp * sin(fi) * D2_D1
                edgeUp.Add(gp_Pnt(X, Y, zUp))
                Cnt = Cnt + 1
            edgeUp.Close()
            self.canva._3dDisplay.DisplayColoredShape(edgeUp.Wire(), 'GREEN', False)
            
        #print "Создали бровки за ", time.time() - startTime, "сек. Число точек = ", Cnt
        

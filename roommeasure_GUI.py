#!/usr/bin/env python3
""" This is a Tkinter based GUI to running DRC/roommeasure.py
"""

from tkinter import *
from tkinter import ttk

import roommeasure as rm
from time import sleep


class RoommeasureGUI():


    def __init__(self, root):
        self.root = root
        self.root.title('DRC/roommeasure.py GUI')
        content =  ttk.Frame( root, padding=(10,10,12,12) )

        # CAP PBK DEVICES
        lbl_scard      = ttk.Label(content, text='SOUND CARD:')
        lbl_cap        = ttk.Label(content, text=' IN:')
        self.combo_cap = ttk.Combobox(content, values=cap_devs)
        lbl_pbk        = ttk.Label(content, text='OUT:')
        self.combo_pbk = ttk.Combobox(content, values=pbk_devs)

        # MEASURE SECTION
        lbl_meastitle    = ttk.Label(content, text='MEASURE:')
        lbl_ch           = ttk.Label(content, text='channels:')
        self.combo_ch    = ttk.Combobox(content, values=channels, width=4)
        lbl_meas         = ttk.Label(content, text='meas per channel:')
        self.combo_meas  = ttk.Combobox(content, values=takes,    width=4)
        lbl_sweep        = ttk.Label(content, text='sweep length:')
        self.combo_sweep = ttk.Combobox(content, values=sweeplen, width=7)
        self.combo_sweep.set('32768')
        lbl_scho         = ttk.Label(content, text='Schoeder freq:')
        self.ent_scho    = ttk.Entry(content,                     width=5)
        self.ent_scho.insert(0, '200')

        # BOTTOM MESSAGES AREA
        self.lbl_msg   = ttk.Label(content, text='a message', font=(None, 20))

        # [Run] BUTTON
        self.btn_go    = ttk.Button(content, text='Go!', command=self.go)

        # GRID ARRANGEMENT
        content.grid(           row=0, column=0, sticky=(N, S, E, W) )

        lbl_scard.grid(         row=0, column=0, sticky=W )
        lbl_cap.grid(           row=1, column=0, sticky=E )
        self.combo_cap.grid(    row=1, column=1)
        lbl_pbk.grid(           row=1, column=2, sticky=E )
        self.combo_pbk.grid(    row=1, column=3)

        lbl_meastitle.grid(     row=2, column=0, sticky=W )
        lbl_ch.grid(            row=3, column=0, sticky=E )
        self.combo_ch.grid(     row=3, column=1, sticky=W )
        lbl_meas.grid(          row=3, column=2, sticky=E )
        self.combo_meas.grid(   row=3, column=3, sticky=W )
        lbl_sweep.grid(         row=3, column=4, sticky=E )
        self.combo_sweep.grid(  row=3, column=5, sticky=W )
        lbl_scho.grid(          row=4, column=4, sticky=E )
        self.ent_scho.grid(     row=4, column=5, sticky=W )

        self.btn_go.grid(       row=6, column=5 )
        self.lbl_msg.grid(      row=7, column=1, columnspan=3, sticky=W )

        # RESIZING BEHAVIOR
        root.rowconfigure(      0, weight=1)
        root.columnconfigure(   0, weight=1)
        for i in range(8):
            content.rowconfigure(   i, weight=1)
        for i in range(3):
            content.columnconfigure(i, weight=1)


    def handle_keypressed(self, event):
        print(f'a key "{event.char}" was pressed')


    def go(self):
        self.lbl_msg['text'] = 'running ...'
        print(f'cap:        {self.combo_cap.get()}')
        print(f'pbk:        {self.combo_pbk.get()}')
        print(f'ch:         {self.combo_ch.get()}')
        print(f'takes:      {self.combo_meas.get()}')
        print(f'Schroeder:  {self.ent_scho.get()}')


if __name__ == '__main__':

    cap_devs = [ x['name'] for x in rm.LS.sd.query_devices()[:] \
                           if x['max_input_channels'] >= 2 ]
    pbk_devs = [ x['name'] for x in rm.LS.sd.query_devices()[:] \
                           if x['max_output_channels'] >= 2 ]
    channels = ['C', 'L', 'R', 'LR']
    takes    = list(range(1,21))
    sweeplen = [2**14, 2**15, 2**16]

    root = Tk()
    app = RoommeasureGUI(root)
    root.mainloop()

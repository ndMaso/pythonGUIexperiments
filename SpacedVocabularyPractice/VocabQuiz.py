import random as r
import pandas as pd
import numpy as np
import time
import tkinter as tk


# Import and process data from xlsx file.
dataframe = pd.read_excel("KoreanVocab.xlsx").applymap(str.strip)
dataframe.loc[:, 'power'] = 1
dataframe.loc[:, 'counter'] = 0
lang1 = dataframe.groupby(['Lang1', 'Grammar'], sort=False).apply(lambda df: list(df['Lang2']))
lang2 = dataframe.groupby(['Lang2', 'Grammar'], sort=False).apply(lambda df: list(df['Lang1']))
# Convert series to frame
lang1 = lang1.to_frame()
lang1.loc[:, 'power'] = 1
lang1.loc[:, 'counter'] = 0
lang2 = lang2.to_frame()
lang2.loc[:, 'power'] = 1
lang2.loc[:, 'counter'] = 0
lang1_grammars = {i: lang1.xs(i, level='Grammar') for i in dataframe.Grammar.unique()}
lang2_grammars = {i: lang2.xs(i, level='Grammar') for i in dataframe.Grammar.unique()}
grammars = dataframe.Grammar.unique()


# Entry point to the question answering loop
def quiz_selector(gui, prompt_language, gram):
    if prompt_language == 1:
        df = lang2_grammars[grammars[gram-1]]
    else:
        df = lang1_grammars[grammars[gram-1]]
    gui(df)
    return


class ExponentialBackoff:
    # Class of helper methods to manipulate the 'counter' and 'power' columns of the dataframes
    @staticmethod
    def decrement_counters(df):
        df.loc[:, 'counter'] = df.loc[:, 'counter'] - df.counter.min()

    @staticmethod
    def new_counter(df, prompt):
        # Generate new counter from 0 to 2**n - 1
        df.loc[prompt, 'counter'] = r.randint(0, (2 ** df.loc[prompt, 'power']) - 1)


class EnterTextGUI:
    def __init__(self, df):
        self.df = df
        self.window = tk.Tk()
        self.lbl_prompt = tk.Label(master=self.window, text=r.choice(self.df.index), foreground="#BA2121",
                                   background="#F7F7F7", font=("", 40, "bold"))
        self.ent_ans = tk.Entry(master=self.window, foreground="#BA2121", background="#F7F7F7",
                                font=("Times New Roman", 40, "bold"))
        self.ent_ans.bind('<Return>', self.check)
        self.lbl_prompt.pack(fill=tk.BOTH, expand=True)
        self.ent_ans.pack(fill=tk.BOTH, expand=True)
        self.window.mainloop()
        self.question()

    def check(self, event):
        prompt = self.lbl_prompt['text']
        if self.ent_ans.get() in self.df.loc[prompt].iloc[0]:
            # Correct answer. Display a tick, codepoint 2714
            self.lbl_prompt['text'] = '\u2714'
            # df.power = df.power - df.power.min() + 1
            self.df.loc[prompt, 'power'] += 1
            ExponentialBackoff.new_counter(self.df, prompt)
            if len(self.df.loc[prompt].iloc[0]) > 1:
                # Multiple valid translations, display all
                self.ent_ans.delete(0, tk.END)
                for word in self.df.loc[prompt].iloc[0]:
                    self.ent_ans.insert(tk.END, word)
                    self.ent_ans.insert(tk.END, ' ')
                    time.sleep(0.3)
                    self.window.update()
        else:
            # Answer wrong. Display a cross, codepoint 2573
            self.lbl_prompt['text'] = '\u2573'
            ExponentialBackoff.new_counter(self.df, prompt)
            # Clear entry and print correct translations slowly
            for i in np.flip(range(len(self.ent_ans.get()))):
                self.ent_ans.delete(i)
                self.window.update()
                time.sleep(0.15)
            for word in self.df.loc[prompt].iloc[0]:
                for i in range(len(word)):
                    self.ent_ans.insert(tk.END, word[i])
                    self.window.update()
                    time.sleep(0.15)
                self.ent_ans.insert(tk.END, ' ')
        self.window.update()
        time.sleep(1)
        self.question()
        self.ent_ans.delete(0, tk.END)

    def question(self):
        ExponentialBackoff.decrement_counters(self.df)
        self.lbl_prompt['text'] = r.choice(self.df[self.df.counter == 0].index)


class MultipleChoiceGUI:
    def __init__(self, df):
        self.df = df
        self.window = tk.Tk()
        self.window.title('quiz')
        self.window.bind('1', self.handle_press)
        self.window.bind('2', self.handle_press)
        self.window.bind('3', self.handle_press)
        self.window.bind('4', self.handle_press)
        self.lbl_prompt = tk.Label(foreground="#BA2121", background="#F7F7F7",
                                   width=10, height=3, font=("", 40, "bold"))
        self.lbl_prompt.pack(fill=tk.BOTH, expand=True)
        self.frm_buttons = tk.Frame(master=self.window)
        for i in range(2):
            for j in range(2):
                frm = tk.Frame(master=self.frm_buttons, relief=tk.GROOVE, borderwidth=5)
                btn = tk.Button(master=frm, foreground="#BA2121", background="#F7F7F7",
                                width=10, height=2, font=("Times New Roman", 40, "bold"))
                lbl = tk.Label(master=frm, text=str(1 + j + i * 2), foreground="#BA2121", background="#F7F7F7",
                               width=1, height=1, font=("Times New Roman", 15, "bold"))
                lbl.grid(row=0, column=0, sticky='nw', padx=5, pady=5)
                btn.bind('<ButtonRelease-1>', self.handle_click)
                frm.bind('<Enter>', self.change_colour_on)
                frm.bind('<Leave>', self.change_colour_off)
                btn.grid(row=0, column=0, sticky='nesw')
                frm.grid(row=i, column=j, padx=5, pady=5, sticky='nesw')
                frm.columnconfigure(0, weight=1, minsize=9)
                frm.rowconfigure(0, weight=1, minsize=9)
        self.frm_buttons.columnconfigure([0, 1], weight=1, minsize=120)
        self.frm_buttons.rowconfigure([0, 1], weight=1, minsize=80)
        self.frm_buttons.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.question()
        self.window.mainloop()

    def handle_click(self, event):
        prompt = self.lbl_prompt['text']
        try:
            right_answer = event.widget['text'] in self.df.loc[prompt].iloc[0]
        except Exception as e:
            print(e)
            return
        if right_answer:
            self.lbl_prompt['text'] = '\u2714'
            for frm in self.frm_buttons.winfo_children():
                frm.winfo_children()[0]['text'] = '\'ㅅ\''
            self.df.loc[prompt, 'power'] += 1
        else:
            self.lbl_prompt['text'] = '\u2573'
            for frm in self.frm_buttons.winfo_children():
                frm.winfo_children()[0]['text'] = 'ㅠㅠ'
        ExponentialBackoff.new_counter(self.df, prompt)
        self.window.after(2000, self.question)

    def handle_press(self, event):
        # In event of number key press instead of click, need to index from window to appropriate button
        event.widget = event.widget.winfo_children()[1].winfo_children()[int(event.char)-1].winfo_children()[0]
        self.handle_click(event)

    def change_colour_on(self, event):
        for wid in event.widget.winfo_children():
            wid['background'] = '#E0E0E0'

    def change_colour_off(self, event):
        for wid in event.widget.winfo_children():
            wid['background'] = "#F7F7F7"

    def question(self):
        ExponentialBackoff.decrement_counters(self.df)
        prompt = r.choice(self.df[self.df.counter == 0].index)
        self.lbl_prompt['text'] = prompt
        answers = ([r.choice(self.df.loc[r.choice(self.df[self.df.counter == 0].index)].iloc[0]) for i in range(3)])
        correct_ind = r.randint(0, 3)
        answers.insert(correct_ind, r.choice(self.df.loc[prompt].iloc[0]))
        for i, frm in enumerate(self.frm_buttons.winfo_children()):
            frm.winfo_children()[0]['text'] = answers[i]


while True:
    gui_ind = input('Select mode:\n\n1: Multiple Choice with GUI\n2: Enter Answer with GUI\n')
    if gui_ind.isdigit():
        break
while True:
    language = input('\n1: Choose Korean Translation\n2: Choose English Translation\n')
    if language.isdigit():
        break
while True:
    g = dataframe.Grammar.unique()
    words = {'n': "nouns", 'v': 'verbs', 'a': 'adjectives', 'ad': 'adverbs'}
    select_prompt = ''
    for i, code in enumerate(g):
        select_prompt += '\n' + str(i+1) + ': ' + words[code]
    grammar = input(select_prompt)
    if grammar.isdigit():
        break
switcher = {1: MultipleChoiceGUI, 2: EnterTextGUI}
quiz_selector(switcher[int(gui_ind)], int(language), int(grammar))
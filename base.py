class Data:
    def __init__(self, data, hl_cur=0):
        """
        Data for popup's displaying

        The popup's row is designed as follow:
        ------ --------------------------------------------
        | ty | | text                                     |
        | pe | | description (won't display if not given) |
        ------ --------------------------------------------

        data: list of row_data, row_data = {'left': '', 'main': '', 'desc': ''}
        index: in range(0, len(data))

        NOTE: The two init_ can help you change (or hold) the position of
        the highlighted row, ie if your returned value is Data type, then
        your highlighted row can not be the first one now.
        """
        self.data = data
        self.n_data = len(data)
        self.hl_cur = min(max(0, hl_cur), self.n_data - 1)

    def run(self, app, idx):
        """
        For overriding

        This function will be called when press <Return> with popup displaying

        Parameters
        ----------
        app : the root Frame, for advanced features
        idx : the index of the highlight row

        Return
        ------
        You can control the popup's behavior through the value you return
        1. 'hold' (lower case) will keep the current popup
        2. an object of Data will update the popup with the new data
        3. an object of Message will display one message,
           then destroy it after some seconds
        4. 'destroy' (lower case) will destroy the app
        5. others will destroy the current popup

        Explanation of above five:
        1. for continuous operations, for example volume adjustment
        2. through it long workflow become possible
        3. for example show error message
        4. finished and quit
        5. for example completion finished

        Advanced
        --------
        app                : tk.Frame
        app.input          : tk.Entry
        app.popup          : tk.Frame
        app.popup.data     : the origin popup data
        """
        pass

    def __len__(self):
        return self.n_data#len(self.data)

    def __getitem__(self, index):
        return self.data[index]

    def __iter__(self):
        return iter(self.data)


class Message:
    __slots__ = ['text', 'ms', 'action']
    def __init__(self, text, ms=2000, action='hide'):
        """
        text: string you want to display, support '\n' etc
        ms  : integer milliseconds before destroying the message
        action: 'hold', 'hide', 'kill'
        """
        self.text = text
        self.ms = ms
        self.action = action

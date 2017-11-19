class Data:
    def __init__(self, data, init_ipage=0, init_index=0):
        """
        Data for popup's displaying

        The popup's row is designed as follow:
        ------ --------------------------------------------
        | ty | | text                                     |
        | pe | | description (won't display if not given) |
        ------ --------------------------------------------

        data: list of row_data, row_data can be any one of
              (text, type, description), (text, type) or (text,),
              but please keep row_data the same shape, or it may looks ugly
        """
        self.data = data
        self.init_ipage = init_ipage
        self.init_index = init_index

    def run(self, app, idx):
        """
        For override

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
        return len(self.data)

    def __getitem__(self, index):
        return self.data[index]

    def __iter__(self):
        return iter(self.data)


class Message:
    __slots__ = ['text', 'ms']
    def __init__(self, text, ms=2000):
        """
        text: string you want to display
        ms  : integer milliseconds before destroying the message
        """
        self.text = text
        self.ms = ms

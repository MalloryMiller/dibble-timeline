


class Flags():
    '''
    A class used to record and manage the flags used when main() is called

    ...

    Attributes
    ----------
    YEARSTART : Integer
        The initial file year chosen
    YEAREND : Integer
        The last file year chosen (inclusive)
    source_flags : List[String]
        a list of all valid source-related flags
    all_flags : List[String]
        a list of all possible valid flags

    Methods
    -------
    add(string)
        Adds a flag to the recorded list of flags to change the settings
    combo_method()
        Returns the combination method of files based on the flags
    chart_type()
        Returns the chart types to generate based on the flags
    sources()
        Returns the sources to use in generation based on the flags
        
    '''


    def __init__(self):
        self.flags=[]
        self.source_v_flags = [
            '-itslive',
            '-measures'
        ]
        self.combo_flags = [
            '-weighted',
            '-average',

        ]
        self.chart_flags = [
            '-points',
            '-elev-error'
        ]

        self.rebuild_flags = [
            '-rebuild',
            '-rebuild:vel',
            '-rebuild:firn',
            '-rebuild:elev',
            '-rebuild:velx',
            '-rebuild:vely',
            '-rebuild:rema',
        ]

        self.point_panel_flags = [
            '-vel',
            '-elev',
            '-grav',
            '-gl',
            '-firn',
        ]

        self.all_flags = ['-datelabel']
        self.all_flags.extend(self.source_v_flags)
        self.all_flags.extend(self.combo_flags)
        self.all_flags.extend(self.chart_flags)
        self.all_flags.extend(self.rebuild_flags)
        self.YEARSTART = 2000
        self.YEAREND = 2025
        



    def add(self, string:str):
        '''
        Adds a flag to the list of activated flags only if it is an existant one.
        If the string isn't a recognized flag, notifies the user but continues.


        Parameters
        ----------
        string : String
            String that appeared in the command, including any trailing -s

        Returns
        -------
        None
        '''
        string = string.lower().strip()
        if (string.split('-')[1]).isdigit() and (string.split('-')[2]).isdigit():
            self.YEARSTART = int(string.split('-')[1])
            self.YEAREND = int(string.split('-')[2])
            return
        
        if string not in self.all_flags:
            print("Urecognized flag: '" + string + "'")

        else:
            self.flags.append(string)


    def label_type(self):
        if '-datelabel' in self.flags:
            return 'date'
        else:
            return 'dist'



    def sources_v(self):
        '''
        Returns the sources to be included based on the flags used.
        Defaults to all sources if no flags are provided


        Parameters
        ----------
        None

        Returns
        -------
        List[String]
            String that reflects one or more of the flags selected in the sources category.
        '''
        
        SOURCES_V = [
            #'Measures',
            'ItsLive',
        ]
                
        source_reset = False
        for x in self.source_v_flags:

            if x in self.flags:
                source_reset = True

        if not source_reset:
            return SOURCES_V
        

        sources = []

        for x in self.flags:
            if x == '-itslive':
                sources.append("ItsLive")
            if x == '-measures':
                sources.append("Measures")

        return sources


    def combo_method(self):
        '''
        Returns the current combination method setting based on the flags used.
        Defaults to 'weighted' if no flags are provided


        Parameters
        ----------
        None

        Returns
        -------
        String
            String that reflects one of the flags selected in the combo category.
        '''

        if '-offset' in self.flags:
            return 'offset'
        elif '-average' in self.flags:
            return 'average'
        else:
            return 'weighted'
        
        

    def rebuilding(self):
        '''
        Returns the current type of chart based on the flags used.
        Defaults to 'nc' if no flags are provided


        Parameters
        ----------
        None

        Returns
        -------
        String
            String that reflects one of the flags selected in the chart category.
        '''
        build_all = False
        to_build = []

        if '-rebuild' in self.flags:
            build_all = True

        for x in self.rebuild_flags:
            if x == '-rebuild':
                continue
            cur = x.split(':')[-1]

            if x in self.flags or build_all:
                to_build.append(cur)

        
        return to_build

    def chart_type(self):
        '''
        Returns the current type of chart based on the flags used.
        Defaults to 'nc' if no flags are provided


        Parameters
        ----------
        None

        Returns
        -------
        String
            String that reflects one of the flags selected in the chart category.
        '''

        if '-points' in self.flags:
            return 'points'
        if '-elev-error' in self.flags:
            return 'elev-error'
        
        return ''

    def point_panels(self):
        panels = []
        for x in self.flags:
            if x in self.point_panel_flags:
                panels.append(x[1:])

        return panels
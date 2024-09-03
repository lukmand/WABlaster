from time import sleep;

class Browser:
    def new_tab(self):
        # open new tab
        self.execute_script('window.open("");')
        sleep(1)
        # switch to new tab
        self.switch_to.window(self.window_handles[-1])
        sleep(1)

    def close_tab(self):
        active_tab = len(self.window_handles)
        if active_tab > 1:
            # close tab
            self.close()
            # switch to tab 1
            self.switch_to.window(self.window_handles[0])

        sleep(1)

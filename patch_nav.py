import sys
with open('src/tuipet/appactions/nav_actions.py') as f:
    t = f.read()

funcs = """
    def action_inventory(self):
            self._open_mode(shopscreen.ShopPanel(self.pet, start_mode="bag"), self._after_shop)

    def action_eggguide(self):
            import tuipet.ui.screens.eggguidescreen as eggguidescreen
            self._open_mode(eggguidescreen.EggGuidePanel(self.pet), lambda _=None: self.repaint())

    def action_datacore(self):
            import tuipet.ui.screens.datacorescreen as datacorescreen
            self._open_mode(datacorescreen.datacorePanel(self.pet), self._after_datacore)

    def _after_datacore(self, msg):
            import tuipet.ui.screens.datacorescreen as datacorescreen
            import tuipet.ui.screens.albumscreen as albumscreen
            if isinstance(msg, tuple) and msg and msg[0] == "album":
                self._open_mode(albumscreen.AlbumPanel(self.pet),
                                lambda _=None: self._open_mode(
                                    datacorescreen.datacorePanel(self.pet, start="TROPHIES"),
                                    self._after_datacore))
"""
t = t.replace('class NavActionsMixin:', 'class NavActionsMixin:' + funcs)
with open('src/tuipet/appactions/nav_actions.py', 'w') as f:
    f.write(t)

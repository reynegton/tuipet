import sys

def replace_in_file(file_path, old, new):
    with open(file_path, 'r') as f:
        text = f.read()
    with open(file_path, 'w') as f:
        f.write(text.replace(old, new))

# Fix self. -> pet. misses (like inside strings or comprehensions)
replace_in_file('src/tuipet/core/pet/care/discipline.py', 'self._set_obedience', 'pet._set_obedience')
replace_in_file('src/tuipet/core/pet/care/discipline.py', 'self.poop', 'pet.poop')
replace_in_file('src/tuipet/core/pet/care/feeding.py', 'self.hunger', 'pet.hunger')

# Import constants in hygiene
replace_in_file('src/tuipet/core/pet/care/hygiene.py', 
                'from tuipet.core.petbase import FullHunger, FullStrength',
                'from tuipet.core.petbase import FullHunger, FullStrength, CLEAN_OBED_INC')

# Import constants in feeding
replace_in_file('src/tuipet/core/pet/care/feeding.py', 
                'from tuipet.core.petbase import FullHunger, FullStrength',
                'from tuipet.core.petbase import FullHunger as FULL_HUNGER, FullStrength, _clamp, PILL_ENERGY_GAIN, PILL_WEIGHT_GAIN')

# Import constants in discipline
replace_in_file('src/tuipet/core/pet/care/discipline.py', 
                'from tuipet.core.petbase import FullHunger, FullStrength',
                'from tuipet.core.petbase import FullHunger, FullStrength, DISOBEY_BELOW, DISOBEY_MAX_P, PRAISE_OBED_INC, SCOLD_OBED_INC')

# Import shop in gifts
replace_in_file('src/tuipet/core/pet/care/gifts.py', 
                'import tuipet.utils.sound as sound',
                'import tuipet.utils.sound as sound\nimport tuipet.core.shop as shop')


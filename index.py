def calculateStrike(baseDmg, enemyArmor):
    modDmg = 0
    try:
        modDmg = baseDmg / enemyArmor
    except ZeroDivisionError:
        print("Error – dragon wins!")
    else:
        modDmg = baseDmg * 0.5
    return modDmg  

calculateStrike(100, 0)
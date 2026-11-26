import unrealsdk
import unrealsdk.unreal as unreal
import random
import math
from mods_base import get_pc, ENGINE
from coroutines import start_coroutine_tick, WaitForSeconds
from BouncyLootGod.bl2.loot_pools import spawn_gear_from_pool, create_modified_item_pool
from BouncyLootGod.bl_tps.ui import display_claptrapped_ui
from BouncyLootGod.pawn import spawn_at_relative, spawn_at_dist
from BouncyLootGod.state import get_or_create_package
from unrealsdk.hooks import Type

traps = {}
def init_game_traps(): 
    try:
        unrealsdk.load_package("GD_Prototype_Streaming_SF")
        keep_alive(unrealsdk.find_object("SkillDefinition", "GD_Prototype_ActionSkill.ActionPackages.ActionPackage_RubberMode"))
        keep_alive(unrealsdk.find_object("SkillDefinition", "GD_Prototype_Skills_GBX.ActionPackages.ActionPackage_ClapInTheBox"))
        keep_alive(unrealsdk.find_object("SkillDefinition", "GD_Prototype_Skills_GBX.ActionPackages.ActionPackage_ClapInTheBox_CountKills"))
        
        unrealsdk.load_package("Eridian_slaughter_Combat")
        traps["Opha"] = clone_pawn("GD_Population_Eridian_Opha.Population.PopDef_Opha_Normal.PopulationFactoryBalancedAIPawn_9",2) #opha
        traps["Pondor"] = clone_pawn("GD_Pet_Population_Guardians.Population.PopDef_GuardianPondor.PopulationFactoryBalancedAIPawn_0") #pondor
        traps["Felicity"] = clone_pawn("GD_DahlCombatSuit_Felicity.Population.PopDef_DahlCombatSuit_Felicity:PopulationFactoryBalancedAIPawn_0") #felicity
        traps["Security_bot"] = clone_pawn("GD_DahlCombatSuit_Mini.Population.PopDef_DahlCombatSuit_Mini:PopulationFactoryBalancedAIPawn_0",4) #security bot
        traps["Flameknuckle"] = clone_pawn("GD_DahlPowersuit_KnuckleRepaired.Population.PopDef_DahlPowersuit_KnuckleRepaired:PopulationFactoryBalancedAIPawn_0",1) #flameknuckle
        traps["Eternal_suit"] = clone_pawn("GD_Pet_Population_Dahl.Mixes.PopDef_Mix_EternalPowersuits:PopulationFactoryBalancedAIPawn_0",2) #eternal suit
        traps["Dahl_rocket"] = clone_pawn("GD_Population_Dahl.Population.PopDef_DahlMix:PopulationFactoryBalancedAIPawn_9", 3) #Rocket
        traps["Dahl_corrosive"] = clone_pawn("GD_Population_Dahl.Mixes.PopMix_Dahl_Elemental_Marines:PopulationFactoryBalancedAIPawn_6", 3) #corrosive
        traps["Dahl_ice"] = clone_pawn("GD_Population_Dahl.Mixes.PopMix_Dahl_Elemental_Marines:PopulationFactoryBalancedAIPawn_4", 3) #ice
        traps["Dahl_flame"] = clone_pawn("GD_Population_Dahl.Mixes.PopMix_Dahl_Elemental_Marines:PopulationFactoryBalancedAIPawn_11", 3) #fire
        traps["Wormhole"] = unrealsdk.find_object("PopulationFactoryInteractiveObject", "GD_DahlEngineerShared.Anims.Anim_DeployWormHole:BehaviorProviderDefinition_0.Behavior_SpawnFromPopulationSystem_11.PopulationFactoryInteractiveObject_1")
        keep_alive(traps["Wormhole"])
    
        unrealsdk.load_package("Deadsurface_Combat")
        unrealsdk.load_package("Deadsurface_Dynamic")
        traps["Nel"] = clone_pawn("GD_Nel.Population.PopDef_Nel:PopulationFactoryBalancedAIPawn_0") #Nel
        traps["Deadlift"] = clone_pawn("GD_SpacemanDeadlift.Population.PopDef_SpacemanDeadlift:PopulationFactoryBalancedAIPawn_2") #Nel
        return True
    except Exception as e:
        print(e)
        return False
pawn_clone_suffix = "_AP_Trap"
def clone_pawn(pawn_factory_def:str, level_offset:int=None):
    pgk = get_or_create_package()
    try:
        factory = unrealsdk.construct_object("PopulationFactoryBalancedAIPawn", pgk, pawn_factory_def.split(':')[-1] + pawn_clone_suffix, 0, unrealsdk.find_object("PopulationFactoryBalancedAIPawn",pawn_factory_def))
        factory.PawnBalanceDefinition = unrealsdk.construct_object("AIPawnBalanceDefinition", pgk, factory.PawnBalanceDefinition.Name + pawn_clone_suffix, 0, factory.PawnBalanceDefinition)
        if level_offset is not None:
            level_offset_str = str(level_offset)
            try:
                lvl_resolver = unrealsdk.find_object("AttributeDefinition", f"{pgk.Name}.EnemyLevel_GameStage_Plus{level_offset_str}")
            except:
                lvl_resolver = unrealsdk.construct_object("AttributeDefinition", pgk, f"EnemyLevel_GameStage_Plus{level_offset_str}", 0, unrealsdk.find_object("AttributeDefinition", "GD_Balance.EnemyLevel.EnemyLevel_GameStage_Plus3"))
                lvl_resolver.ValueResolverChain = [unrealsdk.construct_object("SimpleMathValueResolver", pgk, f"EnemyLevel_GameStage_Plus{level_offset_str}", 0, lvl_resolver.ValueResolverChain[0])]
                lvl_resolver.ValueResolverChain[0].Argument.BaseValueConstant = level_offset
            factory.PawnBalanceDefinition.DefaultExpLevel.BaseValueAttribute = lvl_resolver
        factory.SpawnCostOverride = 0
        factory.UseCostOverride = True
        keep_alive(factory)
        trap_pawn_def.append(factory.PawnBalanceDefinition.Name)
        return  factory
    except Exception as e:
        print(e)
    return None

def keep_alive(obj) -> None:
    obj.ObjectFlags |= 0x4000
    return

def player_active(pc):
    #hudmovie is none while in shops / inventory, oaused for esc menu check
    return pc.GetHudMovie() is not None and not pc.IsPaused()
active_holds = dict()
def add_ticks_or_wait_for_player_active(pc, ticks_to_add_to_existing:int = None, tick_id:str = None):
    hold = active_holds.get(tick_id)
    if hold is None:
        yield from wait_for_player_active(pc, None, tick_id)
    else:
        active_holds[tick_id] += ticks_to_add_to_existing
    yield hold is not None


def wait_for_player_active(pc, ticks_to_hold:int = None, tick_id:str = None):
    if active_holds[tick_id]:
        active_holds[tick_id] += ticks_to_hold or 0
    else:
        active_holds[tick_id] = ticks_to_hold or 0
    while not player_active(pc):
        yield WaitForSeconds(0.2)
    if ticks_to_hold is not None:
        ticks = 0
        while ticks < active_holds[tick_id]:
            if player_active(pc):
                ticks += 1
            yield WaitForSeconds(0.2)
    del active_holds[tick_id]
#TODO: fill this in when implementing generics V2 for TPS
trap_pawn_def = []
fire_weapon_function_name = "WillowGame.WillowWeapon:FireAmmunition"
def hook_into_weapon_fire(name, call, count):
    times_triggered = 0
    def hook_into_weapon_fire_fn(obj: unreal.UObject, args: unreal.WrappedStruct, ret, func: unreal.BoundFunction):
        nonlocal times_triggered
        try:
            call()
        except:
            times_triggered += count
        finally:
            times_triggered += 1

        if times_triggered >= count:
            print("Removing fire hook")
            unrealsdk.hooks.remove_hook(fire_weapon_function_name, Type.PRE, name)
            return
    unrealsdk.hooks.remove_hook(fire_weapon_function_name, Type.PRE, name)
    unrealsdk.hooks.add_hook(
        fire_weapon_function_name,
        Type.PRE,
        name,
        hook_into_weapon_fire_fn
    )


def trigger_game_spawn_trap(spawn_name):
    if spawn_name == "Opha":
        spawn_at_dist(traps[spawn_name], dist=1000)
        spawn_at_dist(traps[spawn_name], dist=-1000)
        display_claptrapped_ui(duration_override=1.5, skill_name_override="Spawn Trap: " + spawn_name)
    elif spawn_name == "Pondor":
        spawn_at_dist(traps[spawn_name], dist=1000)
        spawn_at_dist(traps[spawn_name], dist=-1000)
        display_claptrapped_ui(duration_override=1.5, skill_name_override="Spawn Trap: " + spawn_name)
    elif spawn_name == "Deadlift":
        spawn_at_dist(traps[spawn_name], dist=1000)
        spawn_at_dist(traps[spawn_name], dist=-1000)
        display_claptrapped_ui(duration_override=1.5, skill_name_override="Spawn Trap: " + spawn_name)
    elif spawn_name == "Nel":
        spawn_at_dist(traps[spawn_name], dist=1000)
        spawn_at_dist(traps[spawn_name], dist=-1000)
        display_claptrapped_ui(duration_override=1.5, skill_name_override="Spawn Trap: " + spawn_name)
    elif spawn_name == "Dahl Elementals":
        spawn_at_relative(traps["Dahl_rocket"], x=400, y=400)
        spawn_at_relative(traps["Dahl_rocket"], x=400)
        spawn_at_relative(traps["Dahl_corrosive"], x=400, y=-400)
        spawn_at_relative(traps["Dahl_corrosive"], x=-400)
        spawn_at_relative(traps["Dahl_ice"], x=-400, y=400)
        spawn_at_relative(traps["Dahl_ice"], y=400)
        spawn_at_relative(traps["Dahl_flame"], x=-400, y=-400)
        spawn_at_relative(traps["Dahl_flame"], y=-400)
        display_claptrapped_ui(duration_override=1.5, skill_name_override="Spawn Trap: " + spawn_name)
    elif spawn_name == "Suits":
        spawn_at_relative(traps["Eternal_suit"], x=650, y=650)
        spawn_at_relative(traps["Flameknuckle"], x=650, y=-650)
        spawn_at_relative(traps["Felicity"], x=-650, y=650)
        spawn_at_relative(traps["Security_bot"], x=-650, y=-650)
        display_claptrapped_ui(duration_override=1.5, skill_name_override="Spawn Trap: " + spawn_name)
    elif spawn_name == "Wormhole":
        start_coroutine_tick(spawn_wormholes())
def spawn_wormholes():
    pc = get_pc()
    yield from wait_for_player_active(pc)
    display_claptrapped_ui(duration_override=1.5, skill_name_override="Spawn Trap: Wormhole")
    radius = 700  # yeetus deletus
    vertical = 600  # yeetus deletus
    for _ in range(10):
        rnd = random.random()
        angle = rnd * math.pi * 2
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        z = vertical * rnd
        spawn_at_relative(traps["Wormhole"], x=x, y=y, z=z)
        yield WaitForSeconds(0.07)
        
def trigger_game_trap(trap_name):
    pc = get_pc()
    if trap_name == "Rubber Ducky":
        start_coroutine_tick(trigger_fragtrap_skill(unrealsdk.find_object("SkillDefinition", "GD_Prototype_ActionSkill.ActionPackages.ActionPackage_RubberMode")))
        return True
    elif trap_name == "Clap-in-the-Box":
        start_coroutine_tick(trigger_fragtrap_skill(
            unrealsdk.find_object("SkillDefinition", "GD_Prototype_Skills_GBX.ActionPackages.ActionPackage_ClapInTheBox"), 
            unrealsdk.find_object("SkillDefinition", "GD_Prototype_Skills_GBX.ActionPackages.ActionPackage_ClapInTheBox_CountKills"),
            duration_override=6
            )
         )
        return True

    elif trap_name == "Slippery": #just drop current weapon
        display_claptrapped_ui(duration_override=1.2, skill_name_override=trap_name)
        pc = get_pc()
        def do_slippery():
            if random.random() < 0.93:
                return
            pc.ServerThrowPawnActiveWeapon()
        hook_into_weapon_fire(trap_name, do_slippery, 150)
        
    elif trap_name == "Item Explosion": #throw all items in backpack.
        display_claptrapped_ui(duration_override=1.2, skill_name_override=trap_name)
        pc = get_pc()
        im = pc.GetPawnInventoryManager()
        backpack = im.Backpack[:]
        keep = []
        for item in backpack:
            def_data = getattr(item, "DefinitionData", {})
            definition = getattr(def_data, "BalanceDefinition", None)
            if ".mw_" in str(definition).lower():
                keep.append(item)
            else:
                pc.ServerThrowInventory(item, 1)
        im.Backpack = keep
        #this is needed as the game does not update the internal counter, 
        # leading to "full backpack" error with available slots when trying to pick up items
        im.ServerUpdateBackpackInventoryCount(len(keep))
        
    elif trap_name == "Fling": #fling player in a random direction
        fling_count = 0
        rnd = random.random()
        done = False
        def do_fling(fling_prng = 1):
            nonlocal fling_count, rnd, done
            fling_count += 1
            if done or rnd > (fling_count/fling_prng):
                return
            done = True
            pawn = get_pc().Pawn
            display_claptrapped_ui(duration_override=1.2, skill_name_override=f"Trap: {trap_name}")
            pawn.DoJump(0)
            radius = 4500 #yeetus deletus
            vertical = 2000 #yeetus deletus
            angle = rnd * math.pi * 2
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            pawn.Velocity = unrealsdk.make_struct("Vector", X=x, Y=y, Z=vertical)

        if not player_active(pc):
            hook_into_weapon_fire(trap_name, lambda: do_fling(25), 25)
        else:
            do_fling()
    elif trap_name == "Leaky Wallet": #periodicly leak moonstone / money
        start_coroutine_tick(drop_moonstone_cluster(0.6, 0.5))
    elif trap_name == "Bane":
        pc = get_pc()
        bane_sound = random.choice(["Ake_Cork_UI.Cork_UI_HUD.Ak_Play_Cork_UI_BadAssMedal", "Ake_Marigold_VOSQ_Sidequests.IdTrap.Ak_Play_Dlc_Marigold_VOSQ_IdTrap_0000_IdTrap", "Ake_Cork_VOBD.Cork_VOBD_PL_Prototype.Ak_Play_VOBD_Cork_Prototype_PL_Activate_Psycho_cp"])
        display_claptrapped_ui(duration_override=1.2, skill_name_override=f"Trap: {trap_name}")
        hook_into_weapon_fire(trap_name, lambda: pc.PlayAkEvent(unrealsdk.find_object("AkEvent", bane_sound)), 100)
    elif trap_name == "Upside-down":
        start_coroutine_tick(rotate_player())
    elif trap_name == "FOV":
        start_coroutine_tick(player_fov(165))
    elif trap_name == "Tiny Screen":
        start_coroutine_tick(tiny_player_screen())
    elif trap_name == "No Ammo":
        display_claptrapped_ui(duration_override=1.2, skill_name_override=f"Trap: {trap_name}")
        resource_pools = unrealsdk.find_all("ResourcePool", exact=False)
        for resource_pool in [x for x in resource_pools if str(x.AssociatedProvider).startswith("WillowPlayerController") and str(x.Definition) in ["ResourcePoolDefinition'D_Resourcepools.AmmoPools.Ammo_Grenade_Protean_Pool'", 
                                                                                                                                                    "ResourcePoolDefinition'D_Resourcepools.AmmoPools.Ammo_Combat_Rifle_Pool'",
                                                                                                                                                    "ResourcePoolDefinition'D_Resourcepools.AmmoPools.Ammo_Combat_Shotgun_Pool'",
                                                                                                                                                    "ResourcePoolDefinition'D_Resourcepools.AmmoPools.Ammo_Patrol_SMG_Pool'",
                                                                                                                                                    "ResourcePoolDefinition'D_Resourcepools.AmmoPools.Ammo_Repeater_Pistol_Pool'",
                                                                                                                                                    "ResourcePoolDefinition'D_Resourcepools.AmmoPools.Ammo_Rocket_Launcher_Pool'",
                                                                                                                                                    "ResourcePoolDefinition'D_Resourcepools.AmmoPools.Ammo_Sniper_Rifle_Pool'",
                                                                                                                                                    "ResourcePoolDefinition'D_Resourcepools.AmmoPools.Ammo_Combat_Laser_Pool'",
                                                                                                                                                    "ResourcePoolDefinition'D_Resourcepools.PlayerPools.OxygenPool'",
                                                                                                                                                    # "ResourcePoolDefinition'D_Resourcepools.PlayerPools.ShieldPool'",
                                                                                                                                                    ]]:
            resource_pool.SetCurrentValue(0)
        
    return False
def player_fov(fov, duration=15):
    pc = get_pc()
    appended_to_existing = yield from add_ticks_or_wait_for_player_active(pc, duration*5, 'player_fov')
    if appended_to_existing:
        return
    display_claptrapped_ui(duration_override=duration, skill_name_override="Trap: Field of View")
    fov_bk_default = pc.DefaultFov
    fov_bk_desired = pc.DesiredFov
    pc.DefaultFov = fov
    pc.DesiredFov = fov
    yield from wait_for_player_active(pc, duration*5, 'player_fov')
    pc.DefaultFov = fov_bk_default
    pc.DesiredFov = fov_bk_desired
    
def tiny_player_screen(duration=15):
    pc = get_pc()
    lc = pc.Player
    vp = lc.ViewportClient
    si = vp.SplitscreenInfo
    screen = si[0].PlayerData[0]
    size = 0.2
    appended_to_existing = yield from add_ticks_or_wait_for_player_active(pc, duration*5, 'tiny_player_screen')
    if appended_to_existing:
        return
    hud_gfx = pc.GetHudMovie()
    org_dimensions = hud_gfx.GetViewportDimensions()
    org_viewport_scale = hud_gfx.GetViewportScale()
    org_value_x = screen.SizeX
    org_value_y = screen.SizeY
    org_value_origin_x = screen.OriginX
    org_value_origin_y = screen.OriginY
    screen.SizeX = size
    screen.SizeY = size
    screen.OriginX = random.uniform(0, 1-size)
    screen.OriginY = random.uniform(0, 1-size)
    hud_gfx.SetViewport(int(org_dimensions.X * screen.OriginX), int(org_dimensions.Y * screen.OriginY), int(org_dimensions.X * org_viewport_scale.X * screen.SizeX), int(org_dimensions.Y * org_viewport_scale.Y * screen.SizeY))

    display_claptrapped_ui(duration_override=duration, skill_name_override="Trap: Tiny Screen")
    dir_x = random.choice([-1, 1])
    dir_y = random.choice([-1, 1])
    done = False
    def move_hud(obj: unreal.UObject, args: unreal.WrappedStruct, ret, func: unreal.BoundFunction):
        if done:
            return
        nonlocal dir_x
        nonlocal dir_y
        flipped_x = False
        flipped_y = False
        if screen.OriginX < 0 or screen.OriginX > 1 - size:
            dir_x *= -1
            flipped_x = True
        if screen.OriginY < 0 or screen.OriginY > 1 - size:
            dir_y *= -1
            flipped_y = True
        if flipped_x and flipped_y:
            pc.AddCurrencyOnHand(1, 1)
            pc.PlayAkEvent(unrealsdk.find_object("AkEvent", "Ake_Marigold_Wep_Pistols.Ak_Play_Dlc_Marigold_Wep_PartyPopper_Fire"))
            pc.PlayAkEvent(unrealsdk.find_object("AkEvent", "Ake_Marigold_Wep_Pistols.Ak_Play_Dlc_Marigold_Wep_PartyPopper_Fire"))
            pc.PlayAkEvent(unrealsdk.find_object("AkEvent", "Ake_Marigold_Wep_Pistols.Ak_Play_Dlc_Marigold_Wep_PartyPopper_Fire"))
        next_x = screen.OriginX + (0.0003 * dir_x)
        next_y = screen.OriginY + (0.0002193 * dir_y)
        screen.OriginX = next_x
        screen.OriginY = next_y
        hud_gfx.SetViewport(int(org_dimensions.X * screen.OriginX), int(org_dimensions.Y * screen.OriginY), int(org_dimensions.X * org_viewport_scale.X * screen.SizeX), int(org_dimensions.Y * org_viewport_scale.Y * screen.SizeY))
    unrealsdk.hooks.add_hook(
        "WillowGame.WillowPlayerController:PlayerTick",
        Type.POST,
        "move_hud",
        move_hud
    )

    yield from wait_for_player_active(pc, duration*5, 'tiny_player_screen')
    done = True
    unrealsdk.hooks.remove_hook("WillowGame.WillowPlayerController:PlayerTick", Type.POST, "move_hud")
    yield WaitForSeconds(0.1)
    hud_gfx = pc.GetHudMovie()
    hud_gfx.SetViewport(0,0,int(org_dimensions.X), int(org_dimensions.Y))
    screen.SizeX = org_value_x
    screen.SizeY = org_value_y
    screen.OriginX = org_value_origin_x
    screen.OriginY = org_value_origin_y
    hud = hud_gfx.MyHUDOwner
    hud.ToggleHUD()
    yield WaitForSeconds(0.1)
    hud.ToggleHUD()
    
def rotate_player(duration=15):
    pc = get_pc()
    appended_to_existing = yield from add_ticks_or_wait_for_player_active(pc, duration*5, 'rotate_player')
    if appended_to_existing:
        return
    invert_gamepad =pc.PlayerInput.bInvertGamePad
    invert_gamepad_move =pc.PlayerInput.bInvertGamePadMove
    invert_gamepad_strafe =pc.PlayerInput.bInvertGamePadStrafe
    invert_gamepad_turn =pc.PlayerInput.bInvertGamePadTurn
    invert_mouse =pc.PlayerInput.bInvertMouse
    invert_mouse_turn =pc.PlayerInput.bInvertTurn
    display_claptrapped_ui(duration_override=duration, skill_name_override="Trap: Upside-down")
    pc.Rotation.Roll = 32768
    pc.PlayerInput.bInvertGamePad = not invert_gamepad 
    # pc.PlayerInput.bInvertGamePadMove = not invert_gamepad_move 
    pc.PlayerInput.bInvertGamePadStrafe = not invert_gamepad_strafe 
    pc.PlayerInput.bInvertGamePadTurn = not invert_gamepad_turn 
    pc.PlayerInput.bInvertMouse = not invert_mouse 
    pc.PlayerInput.bInvertTurn = not invert_mouse_turn
    yield from wait_for_player_active(pc, duration*5, 'rotate_player')
    pc.Rotation.Roll = 0
    pc.PlayerInput.bInvertGamePad = invert_gamepad
    # pc.PlayerInput.bInvertGamePadMove = invert_gamepad_move 
    pc.PlayerInput.bInvertGamePadStrafe = invert_gamepad_strafe
    pc.PlayerInput.bInvertGamePadTurn = invert_gamepad_turn
    pc.PlayerInput.bInvertMouse = invert_mouse
    pc.PlayerInput.bInvertTurn = invert_mouse_turn
    
    
    
    
def drop_moonstone_cluster(percentage_to_drop, tick_rate, max_duration=30):
    pc = get_pc()
    yield from add_ticks_or_wait_for_player_active(pc)
    dropped = 0
    moonstone = pc.PlayerReplicationInfo.Currency[1]
    max_to_drop = moonstone.CurrentAmount * percentage_to_drop
    duration = 0
    display_claptrapped_ui(skill_name_override="Leaky Wallet")
    while dropped <= max_to_drop and duration < max_duration:
        yield WaitForSeconds(tick_rate)
        print("Dropping moonstones")
        (item_pool, cleanup_funcs) = create_modified_item_pool("BLGMoonstonePool",inv_bal_def_names=["GD_ItemGrades.Currency.ItemGrade_Currency_Moonstone_Cluster"])
        spawn_gear_from_pool(item_pool, -150, 0, cleanup_funcs=cleanup_funcs, override_loc=None) #spawn behind
        pc.PlayerReplicationInfo.AddCurrencyOnHand(1, -4)
        dropped += 4
        duration += tick_rate
    pc.ClientHudClapTrappedAlertOutro()
    return None
def trigger_fragtrap_skill(skill, after_duration_skill=None, duration_override=None, name_override=None):
    print("Starting "+ str(skill))
    pc = get_pc()
    yield from wait_for_player_active(pc)
    initial_duration = skill.InitialDuration
    if duration_override is not None:
        skill.InitialDuration = duration_override
    constraints = skill.SkillConstraints
    skill.SkillConstraints = [] #remove constraints, to allow triggering subroutine with mis matching conditions
    pc.ServerActivateSkill(skill, None, 5)
    skill.SkillConstraints = constraints
    skill_name = skill.SkillName
    if name_override is not None:
        skill.SkillName = name_override
    display_claptrapped_ui(skill=skill)
    if name_override is not None:
        skill.SkillName = skill_name
    if duration_override is not None:
        skill.InitialDuration = initial_duration
    yield WaitForSeconds(duration_override or skill.InitialDuration)
    pc.ClientHudClapTrappedAlertOutro()
    print("Finishing "+ str(skill))
    if after_duration_skill:
        pc.ServerDeactivateSkill(skill, True)
        pc.ServerActivateSkill(after_duration_skill, None, 5)
    return None
from player import Player
import random
from typing import Tuple, Optional, Dict
from collection_of_cards import CollectionOfCards
import math
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor

class ComputerPlayer(Player):
    def __init__(self, name: str):
        super().__init__(name, is_human=False)
        self.MAX_HAND_SIZE = 20


class RandomStrategyPlayer(ComputerPlayer):
    """Computer player that chooses actions randomly"""
    def choose_first_action(self, game_state: Dict) -> Tuple[str, Optional[int], Optional[Player]]:
        """
        Randomly choose the first action from the allowed actions.
        Returns: (action_type, draw_count, target_player)
        action_type: 'draw', 'take', or 'pass'
        draw_count: number of cards to draw if action is 'draw', None otherwise
        target_player: Player object if action is 'take', None otherwise
        """
        #To prevent having too many cards, actions are restricted based on the current number of cards in the player's hand:
        #Hand size > Maximum hand size - 1: Only Pass is allowed.
        #Hand size > Maximum hand size - 2: Drawing 2 or 3 cards is not allowed.
        #Hand size > Maximum hand size - 3: Drawing 3 cards is not allowed.
        if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 1:
            return ('pass', None, None)
        
        choices = []
        if len(game_state['other_players']) == 1:
            choices = [('draw', 1, None), ('draw', 2, None), ('draw', 3, None), ('take', None, game_state['other_players'][0]), ('pass', None, None)]
        elif len(game_state['other_players']) == 2:
            choices = [('draw', 1, None), ('draw', 2, None), ('draw', 3, None), ('take', None, game_state['other_players'][0]), ('take', None, game_state['other_players'][1]), ('pass', None, None)]

        if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 2:
            choices.remove(('draw', 3, None))
            choices.remove(('draw', 2, None))
        elif len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 3:
            choices.remove(('draw', 3, None))
        
        #When taking cards from other players, if the target player has less than 3 cards, computer player will never take cards from this player to prevent opponent win.
        for player in game_state['other_players']:
            if len(player.cards) <= 2:
                choices.remove(('take', None, player))

        return random.choice(choices)
    

    def choose_second_action(self, game_state: Dict, first_action: str) -> Tuple[str, Optional[int], Optional[Player]]:
        """
        Randomly choose the second action from the available actions.
        If the first action is Draw, the second action can only be Take.
        If the first action is Take, the second action can only be Draw.
        """
        if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 1:
            return ('pass', None, None)
        
        choices = []
        if first_action == 'draw':
            if len(game_state['other_players']) == 1:
                choices = [('take', None, game_state['other_players'][0]), ('pass', None, None)]
            elif len(game_state['other_players']) == 2:
                choices = [('take', None, game_state['other_players'][0]), ('take', None, game_state['other_players'][1]), ('pass', None, None)]

            for player in game_state['other_players']:
                if len(player.cards) <= 2:
                    choices.remove(('take', None, player))
        
        elif first_action == 'take':
            choices = [('draw', 1, None), ('draw', 2, None), ('draw', 3, None), ('pass', None, None)]
            if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 2:
                choices.remove(('draw', 3, None))
                choices.remove(('draw', 2, None))
            elif len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 3:
                choices.remove(('draw', 3, None))
        
        return random.choice(choices)
        
        
    def get_strategy_name(self) -> str:
        return "DEFENSIVE"
    

class ExpectationValueStrategyPlayer(ComputerPlayer):
    """Computer player that calculates expectations before choosing actions"""
    def __init__(self, name: str):
        super().__init__(name)
        self.continuous_pass_count = 0

    
    def choose_first_action(self, game_state: Dict) -> Tuple[str, Optional[int], Optional[Player]]:
        """
        Returns: (action_type, draw_count, target_player)
        action_type: 'draw', 'take', or 'pass'
        draw_count: number of cards to draw if action is 'draw', None otherwise
        target_player: Player object if action is 'take', None otherwise
        """
        #To prevent having too many cards, actions are restricted based on the current number of cards in the player's hand:
        #Hand size > Maximum hand size - 1: Only Pass is allowed.
        #Hand size > Maximum hand size - 2: Drawing 2 or 3 cards is not allowed.
        #Hand size > Maximum hand size - 3: Drawing 3 cards is not allowed.
        if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 1:
            return ('pass', None, None)
        
        expectations = self.calculate_expectation(game_state) 

        if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 2:
            expectations.pop(('draw', 2, None))
            expectations.pop(('draw', 3, None))
        elif len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 3:
            expectations.pop(('draw', 3, None))

        best_action = max(expectations, key=lambda x: expectations[x]) #Extract the action with the highest expected value
        action_type = best_action[0]
        
        #When the number of cards in hand is small, in most cases, the expected value of all actions are negative, except for the pass action, so the computer player will choose to pass repeatedly.
        #Therefore, to prevent the game from stalling, if the computer player passes twice in a row, it must choose another action (draw or take) which has the highest expected value in the next turn, even if those actions have negative expected values.
        if action_type == 'pass':
            self.continuous_pass_count += 1
        else:
            self.continuous_pass_count = 0

        if self.continuous_pass_count > 2:
            expectations.pop(('pass', None, None))
            best_action = max(expectations, key=lambda x: expectations[x])
            action_type = best_action[0]
            self.continuous_pass_count = 0
        
        #When taking cards from other players, if the target player has less than 3 cards, computer player will never take cards from this player to prevent opponent win.
        while action_type == 'take':
            target_player = best_action[2] 
            if len(target_player.cards) <= 2:
                expectations.pop(('take', None, target_player))
                best_action = max(expectations, key=lambda x: expectations[x])
                action_type = best_action[0]
            else:
                return action_type, None, target_player

        if action_type == 'draw':
            draw_count = best_action[1]
            return action_type, draw_count, None
        
        if action_type == 'pass':
            return action_type, None, None
        
        
    def choose_second_action(self, game_state: Dict, first_action: str) -> Tuple[str, Optional[int], Optional[Player]]:
        if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 1:
            return ('pass', None, None)
        
        expectations = self.calculate_expectation(game_state)
        
        #If the first action is Draw, the second action can only be Take.
        #If the first action is Take, the second action can only be Draw.
        if first_action == 'draw':
            expectations = {k: v for k, v in expectations.items() if k[0] != 'draw'}
        elif first_action == 'take':
            expectations = {k: v for k, v in expectations.items() if k[0] != 'take'}

            if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 2:
                expectations.pop(('draw', 2, None))
                expectations.pop(('draw', 3, None))
            elif len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 3:
                expectations.pop(('draw', 3, None))
        
        best_action = max(expectations, key=lambda x: expectations[x])   #Extract the current available action with the highest expected value
        action_type = best_action[0]

        while action_type == 'take':
            target_player = best_action[2] 
            if len(target_player.cards) <= 2:  #When taking cards from other players, if the target player has less than 3 cards, computer player will never take cards from this player to prevent opponent win.
                expectations.pop(('take', None, target_player))
                best_action = max(expectations, key=lambda x: expectations[x]) #Extract the current available action with the second highest expected value, as cannot take cards from this player
                action_type = best_action[0]
            else:
                return action_type, None, target_player

        if action_type == 'draw':
            draw_count = best_action[1]
            return action_type, draw_count, None
        
        if action_type == 'pass':
            return action_type, None, None
        
    def calculate_draw_expectation(self, draw_count: int, game_state: Dict) -> Tuple[Tuple, float]:
        """
        Returns: Tuple: (action ('draw'), draw_count, None), expected_hand_size_reduction_value)
        Mathematical model and details can be found in Computer_Player_Strategies.md (X-DEFENSIVE strategy)
        """
        collection = CollectionOfCards(game_state['current_player'].cards.copy())
        draw_expected_value = 0
        
        #When drawing 1 card, simply loop through all cards in the deck, 
        #temporarily add it to hand, check if there exists a valid group. If so, get the maximum discard count, multiplied by the probability of drawing this card, then remove the card from hand.
        if draw_count == 1:
            for card in game_state['deck_cards']:
                collection.collection.append(card)
                if collection.exist_valid_group():
                    draw_expected_value += collection.find_best_discard_count() * 1 / game_state['deck_size']
                collection.collection.pop()
            return (('draw', 1, None), draw_expected_value - draw_count)
        
        #When drawing 2 or 3 cards, use itertools.combinations to calculate the number of combinations
        #The maximum discard count calculation (find_best_discard_count) is time-consuming, so it is not efficient to loop through all combinations.
        #Therefore, use Monte Carlo sampling to randomly sample a certain number of combinations and calculate the expected value, then estimate the total expected value.
        else:
            combination_count = math.factorial(game_state['deck_size']) // (math.factorial(draw_count) * math.factorial(game_state['deck_size'] - draw_count))
            
            parameter = 1           #Sampling ratio, the smaller the ratio, the more accurate the expected value, but the longer the calculation time.
            sample_list = []        #List of sampled combinations
            if combination_count > 2000:
                parameter = combination_count // 1000
                sample_list = random.sample(list(combinations(game_state['deck_cards'], draw_count)), combination_count // parameter)    
                for combination in sample_list:
                    for card in combination:
                        collection.collection.append(card)
                    if collection.exist_valid_group():
                        draw_expected_value += collection.find_best_discard_count() * 1 / combination_count
                    for card in combination:
                        collection.collection.pop()
            else:                                              #If the number of combinations is less than 2000, simply loop through all combinations
                for combination in combinations(game_state['deck_cards'], draw_count):
                    for card in combination:
                        collection.collection.append(card)
                    if collection.exist_valid_group():
                        draw_expected_value += collection.find_best_discard_count() * 1 / combination_count
                    for card in combination:
                        collection.collection.pop()

            return (('draw', draw_count, None), draw_expected_value * parameter - draw_count)
        

    def calculate_take_expectations(self, game_state: Dict, target_player) -> Tuple[Tuple, float]:
        take_expected_value = 0
        collection = CollectionOfCards(game_state['current_player'].cards.copy())
        for card in target_player.cards:
            collection.collection.append(card)
            if collection.exist_valid_group():
                take_expected_value += collection.find_best_discard_count() * 1 / len(target_player.cards)
            collection.collection.pop()
        return (('take', None, target_player), take_expected_value - 1)
    
    
    def calculate_expectation(self, game_state: Dict) -> Dict[Tuple[str, Optional[int], Optional[Player]], float]:
        """
        Returns: Dictionary: key: action types, value: (expected_value, draw_count, target_player) tuples
        draw_count is None for 'take' and 'pass' actions
        target_player is None for 'draw' and 'pass' actions
        """
        expected_values = {}
        
        #Calculate the expected value for drawing 1, 2, and 3 cards, and taking cards from other players in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as executor:
            draw_futures = [
                executor.submit(self.calculate_draw_expectation, i, game_state) for i in range(1, 4)
            ]
            
            take_futures = [
                executor.submit(self.calculate_take_expectations, game_state, target_player) for target_player in game_state['other_players']
            ]

            for future in draw_futures:
                action, value = future.result()
                expected_values[action] = value

            for future in take_futures:
                action, value = future.result()
                expected_values[action] = value
        
        #As computer player will immediately discard all possible valid groups, there wouldn't exist any valid group at this point, so the expected value of 'pass' action must be 0.
        expected_values[('pass', None, None)] = 0   
        
        return expected_values

        
    def get_strategy_name(self) -> str:
        return "X-DEFENSIVE"
    

class ProbabilityStrategyPlayer(ComputerPlayer):
    """Computer player that calculates probabilities of getting valid groups before choosing actions"""
    def choose_first_action(self, game_state: Dict) -> Tuple[str, Optional[int], Optional[Player]]:
        """
        Returns: (action_type, draw_count, target_player)
        action_type: 'draw', 'take', or 'pass'
        draw_count: number of cards to draw if action is 'draw', None otherwise
        target_player: Player object if action is 'take', None otherwise
        """
        #To prevent having too many cards, actions are restricted based on the current number of cards in the player's hand:
        #Hand size > Maximum hand size - 1: Only Pass is allowed.
        #Hand size > Maximum hand size - 2: Drawing 2 or 3 cards is not allowed.
        #Hand size > Maximum hand size - 3: Drawing 3 cards is not allowed.
        if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 1:
            return ('pass', None, None)
        
        probabilities = self.calculate_probability(game_state)

        if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 2:
            probabilities.pop(('draw', 2, None))
            probabilities.pop(('draw', 3, None))
        elif len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 3:
            probabilities.pop(('draw', 3, None))

        best_action = max(probabilities, key=lambda x: probabilities[x])  #Extract the action with the highest probability
        action_type = best_action[0]

        while action_type == 'take':
            target_player = best_action[2] 
            if len(target_player.cards) <= 2:  #When taking cards from other players, if the target player has less than 3 cards, computer player will never take cards from this player to prevent opponent win.
                probabilities.pop(('take', None, target_player))
                best_action = max(probabilities, key=lambda x: probabilities[x])  #Extract the action with the second highest probability, as cannot take cards from this player
                action_type = best_action[0]
            else:
                return action_type, None, target_player
            
        if action_type == 'draw':
            draw_count = best_action[1]
            return action_type, draw_count, None
        
        if action_type == 'pass':
            return action_type, None, None
        

    def choose_second_action(self, game_state: Dict, first_action: str) -> Tuple[str, Optional[int], Optional[Player]]:       
        if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 1:
            return ('pass', None, None)
        
        probabilities = self.calculate_probability(game_state)
        
        #If the first action is Draw, the second action can only be Take.
        #If the first action is Take, the second action can only be Draw.
        if first_action == 'draw':
            probabilities = {k: v for k, v in probabilities.items() if k[0] != 'draw'}
        elif first_action == 'take':
            probabilities = {k: v for k, v in probabilities.items() if k[0] != 'take'}

            if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 2:
                probabilities.pop(('draw', 2, None))
                probabilities.pop(('draw', 3, None))
            elif len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 3:
                probabilities.pop(('draw', 3, None))
        
        best_action = max(probabilities, key=lambda x: probabilities[x])
        action_type = best_action[0]

        if probabilities[best_action] == 0:
            action_type = 'pass'

        while action_type == 'take':
            target_player = best_action[2] 
            if len(target_player.cards) <= 2:
                probabilities.pop(('take', None, target_player))
                best_action = max(probabilities, key=lambda x: probabilities[x])
                action_type = best_action[0]
            else:
                return action_type, None, target_player
            
        if action_type == 'draw':
            draw_count = best_action[1]
            return action_type, draw_count, None
        
        if action_type == 'pass':
            return action_type, None, None
        

    def calculate_probability(self, game_state: Dict) -> Dict[Tuple[str, Optional[int], Optional[Player]], float]:
        """
        Returns: Dictionary: key: action types, value: probability to obtain valid group with the action
        Mathematical model and details can be found in Computer_Player_Strategies.md (X-AGGRESSIVE strategy)
        """
        collection = CollectionOfCards(game_state['current_player'].cards.copy())
        probabilities = {}
        
        #Calculate probability of obtaining valid group when drawing from deck
        for draw_count in range(1, 4):
            valid_count = 0
            if draw_count == 1:           #Calculating probability of drawing 1 card
                for card in game_state['deck_cards']:
                    collection.collection.append(card)
                    if collection.exist_valid_group():
                        valid_count += 1
                    collection.collection.pop()
                probabilities[('draw', 1, None)] = valid_count / game_state['deck_size']
            
            #Calculating probability of drawing 2 and 3 cards. Use itertools.combinations to efficiently calculate the number of combinations and loop through all combinations
            else:                          
                combination_count = math.factorial(game_state['deck_size']) // (math.factorial(draw_count) * math.factorial(game_state['deck_size'] - draw_count))
                for combination in combinations(game_state['deck_cards'], draw_count):
                    for card in combination:   #For each combination, Temporarily add it to hand, check if there exists a valid group. If so, increment the counter, then remove the combination from the hand.
                        collection.collection.append(card)
                    if collection.exist_valid_group():
                        valid_count += 1
                    for card in combination:
                        collection.collection.pop()
                probabilities[('draw', draw_count, None)] = valid_count / combination_count  #probability is the ratio of valid combinations to total combinations
        
        #Calculate probability of obtaining valid group when taking cards from other players
        for player in game_state['other_players']:
            valid_count = 0
            for card in player.cards:
                collection.collection.append(card)
                if collection.exist_valid_group():
                    valid_count += 1
                collection.collection.pop()
            probabilities[('take', None, player)] = valid_count / len(player.cards)
        
        #As computer player will immediately discard all possible valid groups, there wouldn't exist any valid group at this point, so the probability of 'pass' action must be 0.
        probabilities[('pass', None, None)] = 0

        return probabilities
    
    def get_strategy_name(self) -> str:
        return "X-AGGRESSIVE"


class RulebasedStrategyPlayer(ComputerPlayer):
    """Computer player that chooses actions based on rules"""

    def choose_first_action(self, game_state: Dict) -> Tuple[str, Optional[Player]]:
        # Check if it is worthy to take cards from other players, if so, take, if not, draw.
        # When opponents' hands are more than yours, and
        # opponents have one or more particular cards which could make larger valid group in you hands.
        my_hand = CollectionOfCards(game_state['current_player'].cards)
        hand_count = len(my_hand.collection)
        my_largest_group = my_hand.largest_valid_group()
        worthy_target = []

        for player in game_state['other_players']:
            # player_count = len(player.hand)
            if len(player.cards) <= 2:
                continue
            player_hand = CollectionOfCards(player.cards)
            worthy_or_not = False
            for card in player_hand.collection:
                my_hand.collection.append(card)
                new_largest_group = my_hand.largest_valid_group()
                if my_largest_group != None and new_largest_group != None:
                    if len(new_largest_group) > len(my_largest_group):
                        worthy_or_not = True
                elif my_largest_group == None and new_largest_group != None:
                    worthy_or_not = True
                my_hand.collection.pop()
            if worthy_or_not == True:
                worthy_target.append(player)

        if worthy_target != []:
            if len(worthy_target) == 2:
                player_a = game_state['other_players'][0]
                player_b = game_state['other_players'][1]
                player_a_count = len(player_a.cards)
                player_b_count = len(player_b.cards)
                target_player = None
                if player_a_count > player_b_count and player_a_count > hand_count:
                    target_player = player_a

                if player_a_count < player_b_count and player_b_count > hand_count:
                    target_player = player_b

                if player_a_count == player_b_count and player_b_count > hand_count:
                    target_player = random.choice(worthy_target)

                if target_player is not None:
                    return ('take', None, target_player )
            else:
                other_player = worthy_target[0]
                other_player_count = len(other_player.cards)
                if other_player_count > hand_count :
                    return ('take', None, other_player)

        if hand_count < 8:
            return ('draw', 3, None)
        elif hand_count < 16:
            return ('draw', random.randint(1, 3), None)
        elif hand_count < 20:
            return ('draw', random.randint(0, 1), None)
        else:
            return ('pass', None, None)


    def choose_second_action(self, game_state: Dict, first_action: str) -> Tuple[str, Optional[int], Optional[Player]]:
        if len(game_state['current_player'].cards) > self.MAX_HAND_SIZE - 1:
            return ('pass', None, None)

        my_hand = CollectionOfCards(game_state['current_player'].cards)
        hand_count = len(my_hand.collection)
        my_largest_group = my_hand.largest_valid_group()

        if first_action == 'draw':
            worthy_target = []
            for player in game_state['other_players']:
                # player_count = len(player.hand)
                if len(player.cards) <= 2:
                    continue
                player_hand = CollectionOfCards(player.cards)
                worthy_or_not = False
                for card in player_hand.collection:
                    my_hand.collection.append(card)
                    new_largest_group = my_hand.largest_valid_group()
                    if my_largest_group != None and new_largest_group != None:
                        if len(new_largest_group) > len(my_largest_group):
                            worthy_or_not = True
                    elif my_largest_group == None and new_largest_group != None:
                        worthy_or_not = True
                    my_hand.collection.pop()
                if worthy_or_not == True:
                    worthy_target.append(player)

            if worthy_target != []:
                if len(worthy_target) == 2:
                    player_a = game_state['other_players'][0]
                    player_b = game_state['other_players'][1]
                    player_a_count = len(player_a.cards)
                    player_b_count = len(player_b.cards)
                    target_player = None
                    if player_a_count > player_b_count and player_a_count > hand_count:
                        target_player = player_a

                    if player_a_count < player_b_count and player_b_count > hand_count:
                        target_player = player_b

                    if player_a_count == player_b_count and player_b_count > hand_count:
                        target_player = random.choice(worthy_target)

                    if target_player is not None:
                        return ('take', None, target_player)
                else:
                    other_player = worthy_target[0]
                    other_player_count = len(other_player.cards)
                    if other_player_count > hand_count:
                        return ('take', None, other_player)
            return ('pass', None, None)


        elif first_action == 'take':
            if hand_count < 8:
                return ('draw', 3, None)
            elif hand_count < 16:
                return ('draw', random.randint(1, 3), None)
            elif hand_count < 20:
                return ('draw', random.randint(0, 1), None)
            else:
                return ('pass', None, None)

    def get_strategy_name(self) -> str:
        return "AGGRESSIVE"
# Notty Game

## Requirements

- **Python Version:** Python 3.8 or higher
- **Dependencies:**
  - [PySCIPOpt](https://github.com/SCIP-Interfaces/PySCIPOpt) (Python Interface for SCIP Optimization Suite)
  - [pygame](https://www.pygame.org) (Python Game Development Library)

## Installation

1. **Set Up a Virtual Environment (Optional but Recommended):**

    ```bash
    python -m venv venv
    ```

    Activate the virtual environment:

    - **On Windows:**

        ```bash
        venv\Scripts\activate
        ```

    - **On macOS/Linux:**

        ```bash
        source venv/bin/activate
        ```

3. **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

    **`requirements.txt` Content:**

    ```text
    pyscipopt==5.2.1
    pygame==2.6.1
    ```

## Usage

### Running the Game

To run the game, execute the following command:

1. **Navigate to the Project Root Directory:**

    ```bash
    cd .
    ```

2. **Run the Game:**

    ```bash
    python src/game.py
    ```

## Project Structure

```
NottyGame/
├── src/                   # Source code
│   ├── game.py            # Main game engine and UI, including class Game, GamePhase, OptionBox
│   ├── card.py            # Card class implementation
│   ├── player.py          # Base player class
│   ├── computer_player.py # Computer player classes implementation
│   ├── animations.py      # Card animation system
│   └── collection_of_cards.py # CollectionOfCards class implementation
│
├── assets/
│   ├── cards/            # Card images
│   ├── backgrounds/      # Background image
│   ├── buttons/         # UI button image assets
│   ├── buttons_banned/  # Banned button image assets
│   ├── sound/           # Sound effects
│   └── players/         # Player avatar image assets
│
├── Computer_Player_Strategies.md  # Computer player strategies documentation
├── README.md                  # Project documentation
├── requirements.txt      # Project dependencies
└── config.json          # Game configuration
```

## Technical Implementation

### Core Game Architecture

1. **Game Engine (`game.py`)**
   - Implements the graphical user interface
   - Manages the main game loop, state transitions (through `GamePhase`), game flow control, etc.
   - Player actions:
        - For human players, possible actions in each turn are concretely implemented in methods including `human_draw()`, `human_finish_drawing()`, `human_select_take()`, `human_take()`, `human_pass()`, `human_discard()`, etc. Currently available actions, following the pre-defined game rules, are managed through turn state variables (such as those in `turn_state` dictionary), along with action validation through state checks in action methods.
        - For computer players, turn management is implemented in `computer_turn()`, along with concrete action execution in `computer_draw()`, `computer_take()`, `computer_discard()`, etc.
        - If human player clicks "Play for me" and chooses a desired computer strategy, `let_computer_take_turn()` will initialise a temporary computer player with the same hand cards as the human player, and operate the human's cards based on its corresponding decision-making strategy. 
    - Game flow control:
        - Turn progression:
            - Human player needs to manually click "Next" button to call `human_start_next_turn()` to pass the turn
            - Computer player automatically calls `computer_start_next_turn()` to pass the turn
        - Win condition checking:
            - Empty hand detection
            - Call `show_game_over_popup()` to display a popup when one player wins

2. **Player System**
   - Base `Player` class in `player.py`: with shared functionality
   - Specialized `ComputerPlayer` class in `computer_player.py` with different strategies for automatic decision-making (For detailed information, please refer to **Computer_Player_Strategies.md**); also handles action validation

3. **Card System**
   - `Card` class in `card.py`: Represents individual cards, supporting state and visual effects management (selected, hovering, face up/down, etc.), animations, rendering, positioning, etc.
   - `CollectionOfCards` class in `collection_of_cards.py`: Implements valid group checking and detection, optimal discard strategy, etc.

4. **Animation System (`animations.py`)**
   - Implements card animations, using frame-based animation

5. **Information Display System**
    - Hint system for the human player:
     - `update_hint_calculations()`: Calculates probabilities and expectations values of each available actions, calling `calculate_probability()`, `draw_expectation()`, `take_expectation()` methods from `Player` class, which uses exactly the same logic as the probability and expectation calculations in the computer players' strategies
     - `display_hint_panel()`: Extract calculating results from `_hint_probabilities` and `_hint_expectations` dictionaries, and shows:
       - Probabilities of getting valid groups
       - Expected value of hand size reduction
       - Best discard combinations when having valid groups (when applicable), calling `find_best_discard()` method from `CollectionOfCards` class
   - Valid groups panel:
     - `display_valid_groups_panel()`: Shows all current possible valid groups of current player in real-time

6. **UI and Interaction**
   - Action buttons interaction:
     - Dynamic enabling/disabling action buttons based on game state and provide visual feedback for invalid actions
   - Card interaction:  
     - Visual feedback for card clicking and hovering: `click_card()`, `card_hover()`
     - Visual highlighting of valid groups: `highlight_human_valid_groups()`, `highlight_computer_valid_groups()`
   - Other:
     - Window resizing with dynamic UI adjustment
     - Real-time display messages related to game state, player actions, valid groups, etc.
     - Sound effects for actions


*Additional Note:*
*If choosing X-DEFENSIVE to take over, when several actions have similar expected values, X-DEFENSIVE may select an action that differs from the one showing the highest expected value in the hint panel. This is because the processes for calculating expected values in the hint panel and by the computer player are independent. Both use the same Monte Carlo sampling method to estimate expected values, which introduces minor estimation errors.*

*When the differences in expected values between actions are significant, these errors typically do not affect the ranking of results. However, when the expected values of multiple actions are very close, the errors may lead to differences in results ranking. This does not impact gameplay experience, as the negligible differences in expected values mean that choosing any of the available actions has minimal effect on strategy.*

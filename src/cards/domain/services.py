"""Card progression helpers."""

from dataclasses import dataclass

from src.cards.domain.entities import CardTemplate, PlayerCard
from src.cards.domain.texts import (
    CANT_ASCEND_CARD,
    CANT_UPGRADE_CARD,
)
from src.shared.enums import ResourceType
from src.shared.errors import ValidationError
from src.shared.value_objects.resource_wallet import ResourceWallet
from src.shared.value_objects.stat_block import StatBlock


@dataclass(slots=True)
class CardProgressionService:
    """Level-up, a scend, and form toggle operations."""
    
    level_up_cost: int = 200
    ascend_orb_cost: int = 3
    
    def level_up(self, card: PlayerCard, wallet: ResourceWallet) -> None:
        """Level up a card for coins and one copy."""
        
        if not card.can_level_up():
            raise ValidationError(CANT_UPGRADE_CARD)
        
        wallet.spend(ResourceType.COINS, self.level_up_cost)
        card.level_up()
    
    
    def ascend(self, card: PlayerCard, wallet: ResourceWallet) -> None:
        """Ascend a max-level card for orbs."""
        
        if not card.can_ascend():
            raise ValidationError(CANT_ASCEND_CARD)
        
        wallet.spend(ResourceType.ORBS, self.ascend_orb_cost)
        card.ascend()
    
    
    def toggle_form(self, card: PlayerCard) -> None:
        """Flip the visible form of an ascended card."""
        
        card.toggle_form()


def get_effective_stats(template: CardTemplate, card: PlayerCard) -> StatBlock:
    """Return the stat block of the card in its current form."""
    
    return template.stats_for(card.current_form)

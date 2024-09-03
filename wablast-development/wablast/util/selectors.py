class Selectors:
    CLOSE = 'span[data-icon="x"]'
    
    QR_CODE = 'div[data-ref]:has(canvas)'

    ANIMATING = 'div.app-animating'

    SEARCH_RESULT = '#pane-side div[role="grid"] > div > div:has(div[tabindex="-1"])'

    MESSAGE_BOX = 'footer .copyable-area div[role="textbox"]'
    SEND_BUTTON = 'span[data-icon="send"]'

    SEARCH_BAR = 'div.lexical-rich-text-input > div[role="textbox"]'
    SEARCH_BAR_CLEAR = 'button[aria-label="Cancel search"]'
    SEARCH_BAR_CLEAR_ID = 'button[aria-label*="Batalkan"]'

    NO_CONTACTS_FOUND = 'div[aria-live="polite"]'

    INFO_DRAWER = 'div[data-testid="chat-info-drawer"]'
    INFO_DRAWER_BODY = f'{INFO_DRAWER} section'
    CURRENT_CHAT = 'span[data-testid="conversation-info-header-chat-title"]'

    CONVERSATION_PANEL = '#main'
    # CONVERSATION_HEADER = 'header:has(div[title="Profile Details"])'
    CONVERSATION_HEADER = 'div[title*="Profile"]'
    CONVERSATION_HEADER_ID = 'div[title*="Profil"]'
    CONVERSATION_CURRENT = f'{CONVERSATION_HEADER} > div:nth-child(2) > div > div > span'
    CONVERSATION_CURRENT_ID = f'{CONVERSATION_HEADER_ID} > div:nth-child(2) > div > div > span'
    CONVERSATION_MESSAGES = 'div.message-in'
    CONVERSATION_MENU = f'{CONVERSATION_HEADER} div[role="button"]:has(span[data-icon="menu"])'
    CONVERSATION_MENU_ID = f'{CONVERSATION_HEADER_ID} div[role="button"]:has(span[data-icon="menu"])'
    CONVERSATION_MUTED = f'{INFO_DRAWER} > div:nth-child(5) > div:nth-child(1) div[aria-label]'

    MENU_DROPDOWN = 'div[role="application"] > ul'

    POPUP = 'div[data-animate-modal-popup="true"]'
    POPUP_CONFIRM = f'{POPUP} button:last-child'
    POPUP_CANCEL = f'{POPUP} button:first-child'

    MENU_MUTE = f'{MENU_DROPDOWN} li > div[aria-label="Mute notifications"]'
    MUTE_TIME_OPTIONS = f'{POPUP} label'

    MENU_CLEAR = f'{MENU_DROPDOWN} li > div[aria-label="Clear chat"]'
    MENU_CLEAR_ID = f'{MENU_DROPDOWN} li > div[aria-label="Bersihkan chat"]'
    KEEP_STARRED = f'{POPUP} #menu-icon-clear-chat'

    MENU_PIN = f'{MENU_DROPDOWN} li > div[aria-label="Pin chat"]'
    PIN_ICON = f'{SEARCH_RESULT} span[data-icon="pinned2"]'

    MESSAGE_CONTAINER = 'div.copyable-area' # .copyable-area .message-in div.copyable-text[data-pre-plain-text]
    MESSAGE_INFO = 'div.copyable-text[data-pre-plain-text]'
    MESSAGE_AUTHOR = 'div > span[aria-label]'
    MESSAGE_CONTENT = 'span.selectable-text'
    MESSAGE_META = f'div:nth-child(3) > div> div > div:last-child'
    MESSAGE_FORWARDED = 'span[data-icon="forwarded"]'
    MESSAGE_QUOTE = 'div[aria-label="Quoted Message"]'
    MESSAGE_LINK_PLACEHOLDER = 'span[data-icon="link-placeholder-dark"], span[data-icon="link-placeholder-light"]'

    CHAT_INPUT = '#main div.lexical-rich-text-input > div[role="textbox"]'
    CHAT_INFO_TEXT = f'{INFO_DRAWER} span[dir="auto"].copyable-text.selectable-text'
    CHAT_INFO_PIC = f'{INFO_DRAWER_BODY} > div img'
    CHAT_DEFAULT_PIC = f'{INFO_DRAWER} span[data-icon="default-user"]'
    
    CHAT_DELETE = f'{INFO_DRAWER} div[title="Delete chat"]'
    CHAT_BLOCK = f'{INFO_DRAWER} div[title="Block "]'
    CHAT_UNBLOCK = f'{INFO_DRAWER} div[title="Unblock "]'

    GROUP_INFO_HEADER = 'div[title*="Group"]'
    GROUP_INFO_HEADER_ID = 'div[title*="Grup"]'
    GROUP_SUBJECT = f'span.selectable-text.copyable-text > span[dir="ltr"]'
    GROUP_PARTICIPANTS = f'{INFO_DRAWER} span.selectable-text.copyable-text > span[aria-label=""] > button'
    GROUP_INFO_PIC = CHAT_INFO_PIC
    GROUP_DEFAULT_PIC = f'{INFO_DRAWER} span[data-icon="default-group"]'
    GROUP_DESCRIPTION = f'{INFO_DRAWER_BODY} > div:nth-child(2) span'
    GROUP_READ_MORE = f'{GROUP_DESCRIPTION} + button'
    GROUP_BUTTON_MENU = '#main div[title="Menu"]'

    GROUP_LEAVE = f'{INFO_DRAWER} div[data-testid="li-delete-group"]'

    UNREAD_BADGE = 'div[aria-label="Chat list"] span.aumms1qt'
    UNREAD_TITLE = 'span[title]'
    UNREAD_LAST_MESSAGE = 'div[role="gridcell"] + div span[title]'
    UNREAD_CONVERSATIONS = 'div[aria-label="Chat list"] div[role="listitem"] span[aria-label*="nread"]'
    UNREAD_CONVERSATIONS_ID = 'div[aria-label="Daftar chat"] div[role="listitem"] span[aria-label*="elum"]'
    CONVERSATIONS = 'div[aria-label="Chat list"] div[role="listitem"]'
    CONVERSATIONS_ID = 'div[aria-label="Daftar chat"] div[role="listitem"]'
    UNREAD_CONVERSATIONS_XPATH = '//span[@data-testid="icon-unread-count"]/ancestor::div[@data-testid="cell-frame-container"]'

    VERIFIED_ACCOUNT = 'div[role="listitem"] span[data-icon="psa-verified"]'

    MY_PROFILE_TEXT = 'div[data-testid="drawer-left"] span[data-testid="col-main-profile-input-read-only"]'
    MY_PROFILE_PIC = 'div[data-testid="profile-pic-picker"] img'
    MY_PROFILE_DEFAULT_PIC = 'div[data-testid="profile-pic-picker"] span[data-testid="default-user"]'

    MEDIA_CAPTION = 'div[data-testid="media-caption-input-container"]'

    ATTATCHMENT_MENU = 'div[data-testid="conversation-clip"] > div'
    INPUT_CONTACTS = 'span[data-testid="attach-contact"]'
    INPUT_DOCUMENTS = 'span[data-testid="attach-document"] + input'
    INPUT_MIDIA = 'span[data-testid="attach-image"] + input'

    CONTACT_INFO_PHONE = 'h2 .selectable-text.copyable-text'
    CONTACT_INFO_PHONE2 = 'span div.copyable-area .selectable-text.copyable-text > span'

"""Reusable WPF forms for pyRevit."""

import os
import os.path as op
import string
from collections import OrderedDict
import threading
from functools import wraps

from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit.compat import safe_strtype
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit import framework
from pyrevit.framework import System
from pyrevit.framework import Threading
from pyrevit.framework import Interop
from pyrevit.framework import wpf, Forms, Controls, Media
from pyrevit.api import AdWindows
from pyrevit import revit, UI, DB


logger = get_logger(__name__)


DEFAULT_CMDSWITCHWND_WIDTH = 600
DEFAULT_SEARCHWND_WIDTH = 600
DEFAULT_SEARCHWND_HEIGHT = 100
DEFAULT_INPUTWINDOW_WIDTH = 500
DEFAULT_INPUTWINDOW_HEIGHT = 400


class WPFWindow(framework.Windows.Window):
    r"""WPF Window base class for all pyRevit forms.

    Args:
        xaml_source (str): xaml source filepath or xaml content
        literal_string (bool): xaml_source contains xaml content, not filepath

    Example:
        >>> layout = '<Window ShowInTaskbar="False" ResizeMode="NoResize" ' \
        >>>          'WindowStartupLocation="CenterScreen" ' \
        >>>          'HorizontalContentAlignment="Center">' \
        >>>          '</Window>'
        >>> w = WPFWindow(layout, literal_string=True)
        >>> w.show()
    """

    def __init__(self, xaml_source, literal_string=False):
        """Initialize WPF window and resources."""
        # self.Parent = self
        wih = Interop.WindowInteropHelper(self)
        wih.Owner = AdWindows.ComponentManager.ApplicationWindow

        if not literal_string:
            if not op.exists(xaml_source):
                wpf.LoadComponent(self,
                                  os.path.join(EXEC_PARAMS.command_path,
                                               xaml_source)
                                  )
            else:
                wpf.LoadComponent(self, xaml_source)
        else:
            wpf.LoadComponent(self, framework.StringReader(xaml_source))

        #2c3e50 #noqa
        self.Resources['pyRevitDarkColor'] = \
            Media.Color.FromArgb(0xFF, 0x2c, 0x3e, 0x50)

        #23303d #noqa
        self.Resources['pyRevitDarkerDarkColor'] = \
            Media.Color.FromArgb(0xFF, 0x23, 0x30, 0x3d)

        #ffffff #noqa
        self.Resources['pyRevitButtonColor'] = \
            Media.Color.FromArgb(0xFF, 0xff, 0xff, 0xff)

        #f39c12 #noqa
        self.Resources['pyRevitAccentColor'] = \
            Media.Color.FromArgb(0xFF, 0xf3, 0x9c, 0x12)

        self.Resources['pyRevitDarkBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitDarkColor'])
        self.Resources['pyRevitAccentBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitAccentColor'])

        self.Resources['pyRevitDarkerDarkBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitDarkerDarkColor'])

        self.Resources['pyRevitButtonForgroundBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitButtonColor'])

    def show(self, modal=False):
        """Show window."""
        if modal:
            return self.ShowDialog()
        self.Show()

    def show_dialog(self):
        """Show modal window."""
        return self.ShowDialog()

    def set_image_source(self, element_name, image_file):
        """Set source file for image element.

        Args:
            element_name (str): xaml image element name
            image_file (str): image file path
        """
        wpfel = getattr(self, element_name)
        if not op.exists(image_file):
            # noinspection PyUnresolvedReferences
            wpfel.Source = \
                framework.Imaging.BitmapImage(
                    framework.Uri(os.path.join(EXEC_PARAMS.command_path,
                                               image_file))
                    )
        else:
            wpfel.Source = \
                framework.Imaging.BitmapImage(framework.Uri(image_file))

    @staticmethod
    def hide_element(*wpf_elements):
        """Collapse elements.

        Args:
            *wpf_elements (str): element names to be collaped
        """
        for wpfel in wpf_elements:
            wpfel.Visibility = framework.Windows.Visibility.Collapsed

    @staticmethod
    def show_element(*wpf_elements):
        """Show collapsed elements.

        Args:
            *wpf_elements (str): element names to be set to visible.
        """
        for wpfel in wpf_elements:
            wpfel.Visibility = framework.Windows.Visibility.Visible

    @staticmethod
    def toggle_element(*wpf_elements):
        """Toggle visibility of elements.

        Args:
            *wpf_elements (str): element names to be toggled.
        """
        for wpfel in wpf_elements:
            if wpfel.Visibility == framework.Windows.Visibility.Visible:
                self.hide_element(wpfel)
            elif wpfel.Visibility == framework.Windows.Visibility.Collapsed:
                self.show_element(wpfel)


class TemplateUserInputWindow(WPFWindow):
    """Base class for pyRevit user input standard forms.

    Args:
        context (any): window context element(s)
        title (str): window title
        width (int): window width
        height (int): window height
        **kwargs: other arguments to be passed to :func:`_setup`
    """

    xaml_source = 'BaseWindow.xaml'

    def __init__(self, context, title, width, height, **kwargs):
        """Initialize user input window."""
        WPFWindow.__init__(self,
                           op.join(op.dirname(__file__), self.xaml_source))
        self.Title = title
        self.Width = width
        self.Height = height

        self._context = context
        self.response = None
        self.PreviewKeyDown += self.handle_input_key

        self._setup(**kwargs)

    def _setup(self, **kwargs):
        """Private method to be overriden by subclasses for window setup."""
        pass

    def handle_input_key(self, sender, args):
        """Handle keyboard input."""
        if args.Key == framework.Windows.Input.Key.Escape:
            self.Close()

    @classmethod
    def show(cls, context,
             title='User Input',
             width=DEFAULT_INPUTWINDOW_WIDTH,
             height=DEFAULT_INPUTWINDOW_HEIGHT, **kwargs):
        """Show user input window.

        Args:
            context (any): window context element(s)
            title (type): window title
            width (type): window width
            height (type): window height
            **kwargs (type): other arguments to be passed to window
        """
        dlg = cls(context, title, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response


class SelectFromList(TemplateUserInputWindow):
    """Standard form to select from a list of items.

    Args:
        context (list[str]): list of items to be selected from
        title (str): window title
        width (int): window width
        height (int): window height
        button_name (str): name of select button
        multiselect (bool): allow multi-selection

    Example:
        >>> items = ['item1', 'item2', 'item3']
        >>> SelectFromList.show(items, button_name='Select Item')
        >>> ['item1']
    """

    xaml_source = 'SelectFromList.xaml'

    def _setup(self, **kwargs):
        self.hide_element(self.clrsearch_b)
        self.clear_search(None, None)
        self.search_tb.Focus()

        if 'multiselect' in kwargs and not kwargs['multiselect']:
            self.list_lb.SelectionMode = Controls.SelectionMode.Single
        else:
            self.list_lb.SelectionMode = Controls.SelectionMode.Extended

        button_name = kwargs.get('button_name', None)
        if button_name:
            self.select_b.Content = button_name

        self._list_options()

    def _list_options(self, option_filter=None):
        if option_filter:
            option_filter = option_filter.lower()
            self.list_lb.ItemsSource = \
                [safe_strtype(option) for option in self._context
                 if option_filter in safe_strtype(option).lower()]
        else:
            self.list_lb.ItemsSource = \
                [safe_strtype(option) for option in self._context]

    def _get_options(self):
        return [option for option in self._context
                if safe_strtype(option) in self.list_lb.SelectedItems]

    def button_select(self, sender, args):
        """Handle select button click."""
        self.response = self._get_options()
        self.Close()

    def search_txt_changed(self, sender, args):
        """Handle text change in search box."""
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(option_filter=self.search_tb.Text)

    def clear_search(self, sender, args):
        """Clear search box."""
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.list_lb.ItemsSource = self._context


class BaseCheckBoxItem(object):
    def __init__(self, orig_item):
        self.item = orig_item
        self.state = False

    def __nonzero__(self):
        return self.state

    def __str__(self):
        return self.name or str(self.item)

    @property
    def name(self):
        return getattr(self.item, 'name', '')


class SelectFromCheckBoxes(TemplateUserInputWindow):
    """Standard form to select from a list of check boxes.

    Check box items passed in context to this standard form, must implement
    ``name`` and ``state`` parameter and ``__nonzero__`` method for truth
    value testing.

    Args:
        context (list[object]): list of items to be selected from
        title (str): window title
        width (int): window width
        height (int): window height
        button_name (str): name of select button

    Example:
        >>> class MyOption(object):
        ...     def __init__(self, name, state=False):
        ...         self.state = state
        ...         self.name = name
        ...
        ...     def __nonzero__(self):
        ...         return self.state
        ...
        ...     def __str__(self):
        ...         return self.name
        >>> ops = [MyOption('op1'), MyOption('op2', True), MyOption('op3')]
        >>> res = SelectFromCheckBoxes.show(ops, button_name='Select Item')
        >>> [bool(x) for x in res]  # or [x.state for x in res]
        [True, False, True]
    """

    xaml_source = 'SelectFromCheckboxes.xaml'

    def _setup(self, **kwargs):
        self.hide_element(self.clrsearch_b)
        self.search_tb.Focus()

        self.checked_only = kwargs.get('checked_only', False)
        button_name = kwargs.get('button_name', None)
        if button_name:
            self.select_b.Content = button_name

        self.list_lb.SelectionMode = Controls.SelectionMode.Extended

        self._verify_context()
        self._list_options()

    def _verify_context(self):
        new_context = []
        for item in self._context:
            if not hasattr(item, 'state'):
                new_context.append(BaseCheckBoxItem(item))
            else:
                new_context.append(item)

        self._context = new_context

    def _list_options(self, checkbox_filter=None):
        if checkbox_filter:
            self.checkall_b.Content = 'Check'
            self.uncheckall_b.Content = 'Uncheck'
            self.toggleall_b.Content = 'Toggle'
            checkbox_filter = checkbox_filter.lower()
            self.list_lb.ItemsSource = \
                [checkbox for checkbox in self._context
                 if checkbox_filter in checkbox.name.lower()]
        else:
            self.checkall_b.Content = 'Check All'
            self.uncheckall_b.Content = 'Uncheck All'
            self.toggleall_b.Content = 'Toggle All'
            self.list_lb.ItemsSource = self._context

    def _set_states(self, state=True, flip=False, selected=False):
        all_items = self.list_lb.ItemsSource
        if selected:
            current_list = self.list_lb.SelectedItems
        else:
            current_list = self.list_lb.ItemsSource
        for checkbox in current_list:
            if flip:
                checkbox.state = not checkbox.state
            else:
                checkbox.state = state

        # push list view to redraw
        self.list_lb.ItemsSource = None
        self.list_lb.ItemsSource = all_items

    def toggle_all(self, sender, args):
        """Handle toggle all button to toggle state of all check boxes."""
        self._set_states(flip=True)

    def check_all(self, sender, args):
        """Handle check all button to mark all check boxes as checked."""
        self._set_states(state=True)

    def uncheck_all(self, sender, args):
        """Handle uncheck all button to mark all check boxes as un-checked."""
        self._set_states(state=False)

    def check_selected(self, sender, args):
        """Mark selected checkboxes as checked."""
        self._set_states(state=True, selected=True)

    def uncheck_selected(self, sender, args):
        """Mark selected checkboxes as unchecked."""
        self._set_states(state=False, selected=True)

    def button_select(self, sender, args):
        """Handle select button click."""
        if self.checked_only:
            self.response = [x.item for x in self._context if x.state]
        else:
            self.response = self._context
        self.Close()

    def search_txt_changed(self, sender, args):
        """Handle text change in search box."""
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(checkbox_filter=self.search_tb.Text)

    def clear_search(self, sender, args):
        """Clear search box."""
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.list_lb.ItemsSource = self._context


class CommandSwitchWindow(TemplateUserInputWindow):
    """Standard form to select from a list of command options.

    Args:
        context (list[str]): list of command options to choose from
        switches (list[str]): list of on/off switches
        message (str): window title message
        config (dict): dictionary of config dicts for options or switches

    Returns:
        str: name of selected option

    Returns:
        tuple(str, dict): if ``switches`` option is used, returns a tuple
        of selection option name and dict of switches

    Example:
        This is an example with series of command options:

        >>> ops = ['option1', 'option2', 'option3', 'option4']
        >>> CommandSwitchWindow.show(ops, message='Select Option')
        'option2'

        A more advanced example of combining command options, on/off switches,
        and option or switch configuration options:

        >>> ops = ['option1', 'option2', 'option3', 'option4']
        >>> switches = ['switch1', 'switch2']
        >>> cfgs = {'option1': { 'background': '0xFF55FF'}}
        >>> rops, rswitches = CommandSwitchWindow.show(ops,
        ...                                            switches=switches
        ...                                            message='Select Option',
        ...                                            config=cfgs)
        >>> rops
        'option2'
        >>> rswitches
        {'switch1': False, 'switch2': True}
    """

    xaml_source = 'CommandSwitchWindow.xaml'

    def _setup(self, **kwargs):
        self.selected_switch = ''
        self.Width = DEFAULT_CMDSWITCHWND_WIDTH
        self.Title = 'Command Options'

        message = kwargs.get('message', None)
        self._switches = kwargs.get('switches', [])

        configs = kwargs.get('config', None)

        self.message_label.Content = \
            message if message else 'Pick a command option:'

        # creates the switches first
        for switch in self._switches:
            my_togglebutton = framework.Controls.Primitives.ToggleButton()
            my_togglebutton.Content = switch
            if configs and option in configs:
                self._set_config(my_togglebutton, configs[switch])
            self.button_list.Children.Add(my_togglebutton)

        for option in self._context:
            my_button = framework.Controls.Button()
            my_button.Content = option
            my_button.Click += self.process_option
            if configs and option in configs:
                self._set_config(my_button, configs[option])
            self.button_list.Children.Add(my_button)

        self._setup_response()
        self.search_tb.Focus()
        self._filter_options()

    @staticmethod
    def _set_config(item, config_dict):
        bg = config_dict.get('background', None)
        if bg:
            bg = bg.replace('0x', '#')
            item.Background = Media.BrushConverter().ConvertFrom(bg)

    def _setup_response(self, response=None):
        if self._switches:
            switches = [x for x in self.button_list.Children
                        if hasattr(x, 'IsChecked')]
            self.response = response, {x.Content: x.IsChecked
                                       for x in switches}
        else:
            self.response = response

    def _filter_options(self, option_filter=None):
        if option_filter:
            self.search_tb.Tag = ''
            option_filter = option_filter.lower()
            for button in self.button_list.Children:
                if option_filter not in button.Content.lower():
                    button.Visibility = framework.Windows.Visibility.Collapsed
                else:
                    button.Visibility = framework.Windows.Visibility.Visible
        else:
            self.search_tb.Tag = \
                'Type to Filter / Tab to Select / Enter or Click to Run'
            for button in self.button_list.Children:
                button.Visibility = framework.Windows.Visibility.Visible

    def _get_active_button(self):
        buttons = []
        for button in self.button_list.Children:
            if button.Visibility == framework.Windows.Visibility.Visible:
                buttons.append(button)
        if len(buttons) == 1:
            return buttons[0]
        else:
            for x in buttons:
                if x.IsFocused:
                    return x

    def handle_click(self, sender, args):
        """Handle mouse click."""
        self.Close()

    def handle_input_key(self, sender, args):
        """Handle keyboard inputs."""
        if args.Key == framework.Windows.Input.Key.Escape:
            if self.search_tb.Text:
                self.search_tb.Text = ''
            else:
                self.Close()
        elif args.Key == framework.Windows.Input.Key.Enter:
            self.process_option(self._get_active_button(), None)
        elif args.Key != framework.Windows.Input.Key.Tab \
                and args.Key != framework.Windows.Input.Key.Space\
                and args.Key != framework.Windows.Input.Key.LeftShift\
                and args.Key != framework.Windows.Input.Key.RightShift:
            self.search_tb.Focus()

    def search_txt_changed(self, sender, args):
        """Handle text change in search box."""
        self._filter_options(option_filter=self.search_tb.Text)

    def process_option(self, sender, args):
        """Handle click on command option button."""
        self.Close()
        if sender:
            self._setup_response(response=sender.Content)


class TemplatePromptBar(WPFWindow):
    xaml_source = 'TemplatePromptBar.xaml'

    def __init__(self, height=32, **kwargs):
        WPFWindow.__init__(self,
                           op.join(op.dirname(__file__), self.xaml_source))

        self.user_height = height
        self.update_window()

        self._setup(**kwargs)

    def update_window(self):
        screen_area = HOST_APP.proc_screen_workarea
        scale_factor = 1.0 / HOST_APP.proc_screen_scalefactor
        top = left = width = height = 0

        window_rect = revit.get_window_rectangle()

        # set width and height
        width = window_rect.Right - window_rect.Left
        height = self.user_height

        top = window_rect.Top
        # in maximized window, the top might be off the active screen
        # due to windows thicker window frames
        # lets cut the height and re-adjust the top
        top_diff = abs(screen_area.Top - top)
        if 10 > top_diff > 0 and top_diff < height:
            height -= top_diff
            top = screen_area.Top

        left = window_rect.Left
        # in maximized window, Left also might be off the active screen
        # due to windows thicker window frames
        # let's fix the width to accomodate the extra pixels as well
        left_diff = abs(screen_area.Left - left)
        if 10 > left_diff > 0 and left_diff < width:
            # deduct two times the left negative offset since this extra
            # offset happens on both left and right side
            width -= left_diff * 2
            left = screen_area.Left

        self.Top = top * scale_factor
        self.Left = left * scale_factor
        self.Width = width * scale_factor
        self.Height = height

    def _setup(self, **kwargs):
        pass

    def __enter__(self):
        self.Show()
        return self

    def __exit__(self, exception, exception_value, traceback):
        self.Close()


class WarningBar(TemplatePromptBar):
    xaml_source = 'WarningBar.xaml'

    def _setup(self, **kwargs):
        self.message_tb.Text = kwargs.get('title', '')


class ProgressBar(TemplatePromptBar):
    xaml_source = 'ProgressBar.xaml'

    def _setup(self, **kwargs):
        self.max_value = 1
        self.new_value = 0
        self.step = kwargs.get('step', 0)

        self.cancelled = False
        has_cancel = kwargs.get('cancellable', False)
        if has_cancel:
            self.show_element(self.cancel_b)

        self.pbar.IsIndeterminate = kwargs.get('indeterminate', False)
        self._title = kwargs.get('title', '{value}/{max_value}')

    def _update_pbar(self):
        self.update_window()
        self.pbar.Maximum = self.max_value
        self.pbar.Value = self.new_value

        # updating title
        title_text = \
            string.Formatter().vformat(self._title,
                                       (),
                                       coreutils.SafeDict(
                                           {'value': self.new_value,
                                            'max_value': self.max_value}
                                           ))

        self.pbar_text.Text = title_text

    def _dispatch_updater(self):
        self.pbar.Dispatcher.Invoke(System.Action(self._update_pbar),
                                    Threading.DispatcherPriority.Background)

    @staticmethod
    def _make_return_getter(f, ret):
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            ret.append(f(*args, **kwargs))
        return wrapped_f

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        if type(value) == str:
            self._title = value

    @property
    def indeterminate(self):
        return self.pbar.IsIndeterminate

    @indeterminate.setter
    def indeterminate(self, value):
        self.pbar.IsIndeterminate = value

    def clicked_cancel(self, sender, args):
        self.cancel_b.Content = 'Cancelling...'
        self.cancelled = True

    def wait_async(self, func, args=()):
        returns = []
        self.indeterminate = True
        rgfunc = self._make_return_getter(func, returns)
        t = threading.Thread(target=rgfunc, args=args)
        t.start()
        while t.is_alive():
            self._dispatch_updater()

        return returns[0] if returns else None

    def reset(self):
        self.update_progress(0, 1)

    def update_progress(self, new_value, max_value=1):
        self.max_value = max_value
        self.new_value = new_value
        if self.new_value == 0:
            self._dispatch_updater()
        elif self.step > 0:
            if self.new_value % self.step == 0:
                self._dispatch_updater()
        else:
            self._dispatch_updater()


class SearchPrompt(WPFWindow):
    def __init__(self, search_db, width, height, **kwargs):
        WPFWindow.__init__(self,
                           op.join(op.dirname(__file__), 'SearchPrompt.xaml'))
        self.Width = width
        self.MinWidth = self.Width
        self.Height = height

        self.search_tip = kwargs.get('search_tip', '')

        self._search_db = sorted(search_db)
        self._switches = kwargs.get('switches', [])
        self._setup_response()

        self.search_tb.Focus()
        self.hide_element(self.tab_icon)
        self.hide_element(self.return_icon)
        self.search_tb.Text = ''
        self.set_search_results()

    def _setup_response(self, response=None):
        if self._switches:
            switch_dict = dict.fromkeys(self._switches)
            for mswitch in self.find_switch_match():
                switch_dict[mswitch] = True
            self.response = response, switch_dict
        else:
            self.response = response

    @property
    def search_input(self):
        return self.search_tb.Text

    @search_input.setter
    def search_input(self, value):
        self.search_tb.Text = value

    @property
    def search_term(self):
        return self.search_input.lower().strip()

    @property
    def search_term_noswitch(self):
        term = self.search_term
        for switch in self._switches:
            term = term.replace(switch.lower() + ' ', '')
        return term.strip()

    @property
    def search_matches(self):
        # remove duplicates while keeping order
        # results = list(set(self._search_results))
        return OrderedDict.fromkeys(self._search_results).keys()

    def update_results_display(self, input_term=None):
        self.directmatch_tb.Text = ''
        self.wordsmatch_tb.Text = ''

        results = self.search_matches
        res_cout = len(results)

        logger.debug('unique results count: {}'.format(res_cout))
        logger.debug('unique results: {}'.format(results))

        if res_cout > 1:
            self.show_element(self.tab_icon)
            self.hide_element(self.return_icon)
        elif res_cout == 1:
            self.hide_element(self.tab_icon)
            self.show_element(self.return_icon)
        else:
            self.hide_element(self.tab_icon)
            self.hide_element(self.return_icon)

        if self._result_index >= res_cout:
            self._result_index = 0

        if self._result_index < 0:
            self._result_index = res_cout - 1

        if not input_term:
            input_term = self.search_term_noswitch

        if not self.search_input:
            self.directmatch_tb.Text = self.search_tip
            return

        if results:
            cur_res = results[self._result_index]
            logger.debug('current result: {}'.format(cur_res))
            if cur_res.lower().startswith(input_term):
                logger.debug('directmatch_tb.Text: {}'.format(cur_res))
                self.directmatch_tb.Text = \
                    self.search_input + cur_res[len(input_term):]
            else:
                logger.debug('wordsmatch_tb.Text: {}'.format(cur_res))
                self.wordsmatch_tb.Text = '- {}'.format(cur_res)

            self._setup_response(cur_res)
            return True

        self._setup_response()
        return False

    def set_search_results(self, *args):
        self._result_index = 0
        self._search_results = []

        for resultset in args:
            logger.debug('result set: {}'.format(resultset))
            self._search_results.extend(sorted(resultset))

        logger.debug('results: {}'.format(self._search_results))

    def find_switch_match(self):
        results = []
        cur_txt = self.search_term
        for switch in self._switches:
            if switch.lower() in cur_txt:
                results.append(switch)
        return results

    def find_direct_match(self, input_text):
        results = []
        if input_text:
            for cmd_name in self._search_db:
                if cmd_name.lower().startswith(input_text):
                    results.append(cmd_name)

        return results

    def find_word_match(self, input_text):
        results = []
        if input_text:
            cur_words = input_text.split(' ')
            for cmd_name in self._search_db:
                if all([x in cmd_name.lower() for x in cur_words]):
                    results.append(cmd_name)

        return results

    def search_txt_changed(self, sender, args):
        input_term = self.search_term_noswitch
        dmresults = self.find_direct_match(input_term)
        wordresults = self.find_word_match(input_term)
        self.set_search_results(dmresults, wordresults)
        self.update_results_display(input_term)

    def handle_kb_key(self, sender, args):
        if args.Key == framework.Windows.Input.Key.Escape:
            self._setup_response()
            self.Close()
        elif args.Key == framework.Windows.Input.Key.Enter:
            self.Close()
        elif args.Key == framework.Windows.Input.Key.Tab:
            self._result_index += 1
            self.update_results_display()
        elif args.Key == framework.Windows.Input.Key.Down:
            self._result_index += 1
            self.update_results_display()
        elif args.Key == framework.Windows.Input.Key.Up:
            self._result_index -= 1
            self.update_results_display()

    @classmethod
    def show(cls, search_db,
             width=DEFAULT_SEARCHWND_WIDTH,
             height=DEFAULT_SEARCHWND_HEIGHT, **kwargs):
        dlg = cls(search_db, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response


def alert(msg, title='pyRevit',
          cancel=False, yes=False, no=False, retry=False):
    buttons = UI.TaskDialogCommonButtons.Ok

    if any([cancel, yes, no, retry]):
        buttons = UI.TaskDialogCommonButtons.None   # noqa

        if cancel:
            buttons |= UI.TaskDialogCommonButtons.Cancel
        if yes:
            buttons |= UI.TaskDialogCommonButtons.Yes
        if no:
            buttons |= UI.TaskDialogCommonButtons.No
        if retry:
            buttons |= UI.TaskDialogCommonButtons.Retry

    res = UI.TaskDialog.Show(title, msg, buttons)

    if res == UI.TaskDialogResult.Ok \
            or res == UI.TaskDialogResult.Yes \
            or res == UI.TaskDialogResult.Retry:
        return True
    else:
        return False


def pick_folder():
    fb_dlg = Forms.FolderBrowserDialog()
    if fb_dlg.ShowDialog() == Forms.DialogResult.OK:
        return fb_dlg.SelectedPath


def pick_file(file_ext='', files_filter='', init_dir='',
              restore_dir=True, multi_file=False, unc_paths=False):
    of_dlg = Forms.OpenFileDialog()
    if files_filter:
        of_dlg.Filter = files_filter
    else:
        of_dlg.Filter = '|*.{}'.format(file_ext)
    of_dlg.RestoreDirectory = restore_dir
    of_dlg.Multiselect = multi_file
    if init_dir:
        of_dlg.InitialDirectory = init_dir
    if of_dlg.ShowDialog() == Forms.DialogResult.OK:
        if unc_paths:
            return coreutils.dletter_to_unc(of_dlg.FileName)
        return of_dlg.FileName


def save_file(file_ext='', files_filter='', init_dir='', default_name='',
              restore_dir=True, unc_paths=False):
    sf_dlg = Forms.SaveFileDialog()
    if files_filter:
        sf_dlg.Filter = files_filter
    else:
        sf_dlg.Filter = '|*.{}'.format(file_ext)
    sf_dlg.RestoreDirectory = restore_dir
    if init_dir:
        sf_dlg.InitialDirectory = init_dir

    # setting default filename
    sf_dlg.FileName = default_name

    if sf_dlg.ShowDialog() == Forms.DialogResult.OK:
        if unc_paths:
            return coreutils.dletter_to_unc(sf_dlg.FileName)
        return sf_dlg.FileName


class RevisionOption(object):
    def __init__(self, revision_element):
        self.revision_element = revision_element

    def __str__(self):
        revnum = self.revision_element.SequenceNumber
        if hasattr(self.revision_element, 'RevisionNumber'):
            revnum = self.revision_element.RevisionNumber
        return '{}-{}-{}'.format(revnum,
                                 self.revision_element.Description,
                                 self.revision_element.RevisionDate)


class SheetOption(object):
    def __init__(self, sheet_element):
        self.state = False
        self.sheet_element = sheet_element
        self.name = '{} - {}'.format(self.sheet_element.SheetNumber,
                                     self.sheet_element.Name)
        self.number = self.sheet_element.SheetNumber

    def __nonzero__(self):
        return self.state

    def __str__(self):
        return self.name


def select_revisions(title='Select Revision',
                     button_name='Select',
                     width=DEFAULT_INPUTWINDOW_WIDTH,
                     multiselect=True):
    revisions = sorted(revit.query.get_revisions(),
                       key=lambda x: x.SequenceNumber)
    revision_options = [RevisionOption(x) for x in revisions]

    # ask user for revisions
    return_options = \
        SelectFromList.show(
            revision_options,
            title=title,
            button_name=button_name,
            width=width,
            multiselect=multiselect
            )

    if return_options:
        if not multiselect and len(return_options) == 1:
            return return_options[0].revision_element
        else:
            return [x.revision_element for x in return_options]


def select_sheets(title='Select Sheets', button_name='Select',
                  width=DEFAULT_INPUTWINDOW_WIDTH, multiple=True):
    all_sheets = DB.FilteredElementCollector(revit.doc) \
                   .OfClass(DB.ViewSheet) \
                   .WhereElementIsNotElementType() \
                   .ToElements()

    # ask user for multiple sheets
    if multiple:
        return_options = \
            SelectFromCheckBoxes.show(
                sorted([SheetOption(x) for x in all_sheets],
                       key=lambda x: x.number),
                title=title,
                button_name=button_name,
                width=width)
        if return_options:
            return [x.sheet_element for x in return_options if x.state]
    else:
        return_option = \
            SelectFromList.show(
                sorted([SheetOption(x) for x in all_sheets],
                       key=lambda x: x.number),
                title=title,
                button_name=button_name,
                width=width,
                multiselect=False)
        if return_option:
            return return_option[0].sheet_element


def check_workshared(doc):
    if not doc.IsWorkshared:
        alert('Model is not workshared.')
        return False
    return True
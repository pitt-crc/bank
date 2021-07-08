#!/usr/bin/env perl
use strict;
use warnings;

# Need a begin and end dates, choose the whole year
my $year = `date +%y`;
my $begin = "01/01/" . $year;
my $end = `date +%m/%d/%y`;

# Check that an account was specified
my $num_argv = $#ARGV + 1;
if ( $num_argv != 1) {
    print("ERROR, usage: ./crc-usage.pl <account>");
    exit;
}
my $account = $ARGV[0];

# Get SUs from crc-bank.py
my $line = `/ihome/crc/wrappers/crc-sus.py $account`;
my @sp = split(' ', $line);
my $sus = $sp[5];

# Print Header
print('-' x 61 . "\n");
printf("Total SUs: %50i\n", $sus);
print('-' x 61 . "\n");

my @clusters = qw( smp gpu mpi );
foreach my $cluster (@clusters) {
    if ($sus == 0) {
        print("Your account has no SUs on this cluster\n");
    }
    elsif ( $sus == -1 ) {
        print("Your account has unlimited SUs on this cluster\n");
    }
    else {
        my @usage = `sshare --all --noheader --format=user%30,rawusage%30 --accounts=$account --cluster=$cluster`;
        
        # Cluster Header
        print('-' x 91 . "\n");
        printf("%8s %3s\n", "Cluster:", $cluster);
        
        # First line contains the Total SUs
        my @sp = split(' ', $usage[1]);
        $sp[-1] = $sp[-1]  / (60 * 60);
        printf("%10s: %10i (%6.2f%1s)\n", "Cluster Total (Percent)", $sp[-1], 100 * $sp[-1] / $sus, "%");

        # Print the Users
        printf("%30s %30s %30s\n", "User", "SUs (CPU Hours)", "Percent of Total SUs");
        printf("%30s %30s %30s\n", '-' x 30, '-' x 30, '-' x 30);

        # Loop over usage lines, replace cpu seconds with cpu hours
        # -> with Slurm Clusters you need to start on second line
        for (my $i = 2; $i < @usage; $i++) {
            # Split the line, convert to CPU Hours
            my @sp = split(' ', $usage[$i]);
            $sp[-1] = $sp[-1]  / (60 * 60);
            # Need this line for the total, otherwise columns are incorrect
            #if (scalar(@sp) == 2) {
            #    splice(@sp, 1, 0, '');
            #}
            # Print out the strings, SUs, and Percent of Total
            printf("%30s " x $#sp, @sp[0 .. $#sp - 1]);
            printf("%30i", $sp[-1]);
            printf("%30.4f\n", 100 * $sp[-1] / $sus);
        }
    }
}
